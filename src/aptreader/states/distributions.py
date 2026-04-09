"""Distributions browsing page."""
# required because of sqlmodel stuff with selectinload etc
# pyright: reportArgumentType=false

import logging
import time
from collections.abc import AsyncIterator
from math import floor
from time import perf_counter
from typing import Any

import anyio
import reflex as rx
import sqlalchemy as sa
import sqlmodel as sm
from sqlalchemy.orm import defer, selectinload
from sqlmodel.ext.asyncio.session import AsyncSession

from aptreader.fetcher import (
    download_packages_index,
    iter_packages_entries_async,
)
from aptreader.models import Architecture, Component, Distribution, Package
from aptreader.states.repo_select import RepoSelectState
from aptreader.utils import clean_text, long_running_task, utcnow

logger = logging.getLogger("aptreader.states.distributions")

# fmt: off
ORDERED_COMPONENTS = [
    "main", "contrib", "non-free", "non-free-firmware",
    "restricted", "universe", "multiverse",
]
N_ORDERED_COMPONENTS = len(ORDERED_COMPONENTS)

ORDERED_ARCHITECTURES = [
    "i386", "amd64", "amd64v3",
    "armel", "armhf", "arm64", "aarch64",
    "riscv32", "riscv64",
    "mipsel", "mips64el",
    "la64", "loongarch64",
    "powerpc", "ppc32", "ppc64el",
    "s390", "s390x",
]
N_ORDERED_ARCHITECTURES = len(ORDERED_ARCHITECTURES)
# fmt: on


class DistributionsState(RepoSelectState):
    _repo_dists: rx.Field[list[Distribution]] = rx.field(default_factory=list)
    _filtered_dists: rx.Field[list[Distribution]] = rx.field(default_factory=list)
    _last_repo_id: rx.Field[int] = rx.field(-1)

    component_filter: str = "all"
    architecture_filter: str = "all"

    dist_sort_val: str = "date"
    dist_sort_reverse: bool = False
    search_value: str = ""

    page_offset: rx.Field[int] = rx.field(0)
    page_size: rx.Field[int] = rx.field(25)

    package_fetching: bool = False
    package_fetch_distribution_id: int = -1
    package_fetch_progress: int = 0
    package_fetch_message: str = ""

    @rx.var
    def page_size_str(self) -> str:
        return str(self.page_size)

    @rx.var
    def page(self) -> list[Distribution]:
        logger.debug(
            f"Getting page: offset={self.page_offset}, size={self.page_size}, "
            f"total_filtered={len(self._filtered_dists)}"
        )
        return self._filtered_dists[self.page_offset : self.page_offset + self.page_size]

    @rx.var
    def page_number(self) -> int:
        return (self.page_offset // self.page_size) + 1

    @rx.var
    def total_pages(self) -> int:
        return len(self._filtered_dists) // self.page_size + (
            1 if len(self._filtered_dists) % self.page_size else 0
        )

    @rx.event
    def prev_page(self):
        self.page_offset = max(self.page_offset - self.page_size, 0)

    @rx.event
    def next_page(self):
        # if self.page_offset + self.page_size < len(self._filtered_dists):
        self.page_offset += self.page_size

    @rx.event
    def change_page_size(self, value: str):
        self.page_size = max(int(value), 10)

    @rx.event
    async def load_distributions(self):
        start_ts = perf_counter()
        # ensure dependency is loaded

        current_repo_id = self.current_repo_id
        if current_repo_id == -1:
            return []

        async with rx.asession() as session:
            query = (
                sm.select(Distribution)
                .where(Distribution.repository_id == sa.bindparam("repo_id"))
                .options(
                    defer(Distribution.raw, raiseload=True),
                )
            )
            sort_dir = sm.desc if self.dist_sort_reverse else sm.asc

            match self.dist_sort_val:
                case "name":
                    query = query.order_by(sort_dir(Distribution.name))
                case "package_count":
                    query = query.order_by(sort_dir(Distribution.package_count))
                case "date":
                    query = query.order_by(sort_dir(Distribution.date))
                case _:
                    query = query.order_by(sort_dir(Distribution.date))

            result = await session.exec(query, params=dict(repo_id=current_repo_id))
            dists = result.all()
            end_ts = perf_counter()
            query_time = end_ts - start_ts
            logger.info(
                f"Loaded {len(dists)} distributions for repository ID {current_repo_id} in {query_time:.2f} seconds."
            )
        self._repo_dists = list(dists)
        return DistributionsState.filter_distributions

    @rx.event
    def filter_distributions(self):
        """Load distributions for the current repository."""
        comp_filter = self.get_value("component_filter")
        arch_filter = self.get_value("architecture_filter")
        search_value = self.get_value("search_value")

        logger.info(
            f"Filtering distributions: total={len(self._repo_dists)}, "
            f"component='{comp_filter}', architecture='{arch_filter}', "
            f"search='{search_value}')"
        )

        self._filtered_dists = []

        dists = []
        for dist in self.get_value("_repo_dists"):
            if comp_filter != "all" and comp_filter not in dist.component_names:
                continue
            if arch_filter != "all" and arch_filter not in dist.architecture_names:
                continue
            if search_value:
                search_value = search_value.lower()
                search_in = dist.name.lower() + (dist.codename.lower() if dist.codename else "")
                if search_value not in search_in:
                    continue
            dists.append(dist)

        self._filtered_dists = dists
        self.page_offset = 0

        total_dists = len(self._filtered_dists)
        _filtered_dists = len(self._filtered_dists)
        logger.info(
            f"Filtered distributions: {_filtered_dists} / {total_dists} "
            f"(component='{comp_filter}', architecture='{arch_filter}', "
            f"search='{search_value}')"
        )

    @rx.event
    def change_component_filter(self, value: str):
        if not value:
            logger.warning("Empty component filter value received, defaulting to 'all'")
            self.component_filter = "all"
        else:
            logger.debug(f"Changing component filter to '{value}'")
            self.component_filter = value or "all"
        return DistributionsState.filter_distributions

    @rx.event
    def change_architecture_filter(self, value: str):
        if not value:
            logger.warning("Empty architecture filter value received, defaulting to 'all'")
            self.architecture_filter = "all"
        else:
            logger.debug(f"Changing architecture filter to '{value}'")
            self.architecture_filter = value or "all"
        return DistributionsState.filter_distributions

    @rx.event
    def change_search_value(self, value: str):
        if not value:
            logger.debug("Clearing search value")
            self.search_value = ""
        else:
            logger.debug(f"Changing search value to '{value}'")
            self.search_value = value
        return DistributionsState.filter_distributions

    @rx.var
    async def available_components(self) -> list[str]:
        comps = set()
        for dist in self._repo_dists:
            for comp in dist.component_names:
                comps.add(comp)
        return ["all"] + sorted(comps)

    @rx.var
    async def available_architectures(self) -> list[str]:
        archs = set()
        for dist in self._repo_dists:
            for arch in dist.architecture_names:
                archs.add(arch)

        return ["all"] + sorted(archs)

    @rx.var
    async def distribution_names(self) -> list[str]:
        """Get the list of distribution names for the current repository."""
        return [dist.name for dist in self._repo_dists]

    async def _get_dist_by_id(self, distribution_id: int) -> Distribution | None:
        """Get a distribution by its ID from the cached list."""
        for dist in self._repo_dists:
            if dist.id == distribution_id:
                return dist
        return None

    @long_running_task
    @rx.event(background=True)
    async def fetch_packages_for_distribution(self, distribution_id: int | None):
        """Download and persist Packages indexes for a distribution."""
        if distribution_id is None:
            msg = "No distribution ID provided for package fetch."
            logger.error(msg)
            yield rx.toast.error(msg, duration=10000)
            return

        repo = self.current_repo
        if repo is None:
            msg = "No repository selected for package fetch."
            logger.error(msg)
            yield rx.toast.error(msg, duration=10000)
            return

        async with self:
            dist = await self._get_dist_by_id(distribution_id)
        if not dist:
            msg = f"Distribution with ID {distribution_id} not found in cached distributions."
            logger.error(msg)
            yield rx.toast.error(msg, duration=10000)
            return

        if not repo:
            msg = f"Distribution #{distribution_id} has no associated repository."
            logger.error(msg)
            yield rx.toast.error(msg, duration=10000)
            return
        repo_url = repo.url
        name = dist.name
        codename = dist.codename or name
        component_names = dist.component_names or []
        architecture_names = dist.architecture_names or []

        if not component_names or not architecture_names:
            msg = "Distribution metadata missing components/architectures."
            logger.error(msg)
            yield rx.toast.error(msg, duration=10000)
            return

        targets = [(comp, arch) for comp in component_names for arch in architecture_names]
        total_targets = len(targets)

        async with self:
            self.package_fetch_progress = 0
            self.package_fetch_message = f"Preparing package sync for {name}"
            self.package_fetching = True
        yield

        total_packages = 0
        processed = 0
        try:
            for comp_name, arch_name in targets:
                name_tag = f"{name} target {processed + 1}/{total_targets} ({comp_name}/{arch_name})"
                async with self:
                    self.package_fetch_message = f"{name_tag}: downloading Packages index..."
                yield

                download_result = await download_packages_index(repo_url, name, comp_name, arch_name)
                if not download_result:
                    logger.info(f"No Packages file for {comp_name}/{arch_name}")
                    processed += 1
                    async with self:
                        self.package_fetch_progress = floor((processed / total_targets) * 100)
                    yield
                    continue

                _, local_path = download_result
                new_count = 0
                try:
                    pkg_iter = iter_packages_entries_async(local_path)
                    async for count in _replace_packages_for_target(
                        distribution_id,
                        comp_name,
                        arch_name,
                        pkg_iter,
                    ):
                        async with self:
                            self.package_fetch_message = f"{name_tag}: imported {count} packages..."
                        new_count = count
                        yield
                    total_packages += new_count
                except Exception as write_error:
                    logger.exception("Failed to save packages for %s/%s", comp_name, arch_name)
                    yield rx.toast.error(f"Error saving {name_tag}: {write_error}", duration=10000)
                    # wait a moment to let user see the error
                    await anyio.sleep(1)
                finally:
                    processed += 1
                    async with self:
                        self.package_fetch_progress = floor((processed / total_targets) * 100)
                        self.package_fetch_message = f"{name_tag}: imported {new_count} new packages"
                    yield
            async with self:
                self.package_fetch_progress = 100
                self.package_fetch_message = f"Package sync complete ({total_packages} packages)"
            yield rx.toast.success(
                f"Fetched {total_packages} packages for {codename} across {processed} component/arch pairs"
            )

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Error fetching packages for distribution %s", distribution_id)
            yield rx.toast.error(f"Error fetching packages: {exc}")
        finally:
            async with self:
                self.package_fetching = False
                self.package_fetch_distribution_id = -1
                self.package_fetch_progress = 100
                self.package_fetch_message = ""
            yield


def _build_package_model(
    entry: dict[str, Any],
    distribution: Distribution,
    component: Component,
    architecture: Architecture,
) -> Package | None:
    name = entry.get("Package")
    version = entry.get("Version")
    if not name or not version:
        return None
    if not distribution.id or not component.id or not architecture.id:
        return None

    return Package(
        name=name,
        version=version,
        section=entry.get("Section"),
        priority=entry.get("Priority"),
        size=entry.get("Size"),
        installed_size=entry.get("Installed-Size"),
        filename=entry.get("Filename"),
        source=entry.get("Source"),
        maintainer=entry.get("Maintainer"),
        homepage=entry.get("Homepage"),
        description=clean_text(entry.get("Description")),
        description_md5=entry.get("Description-md5"),
        checksum_md5=entry.get("MD5sum"),
        checksum_sha1=entry.get("SHA1"),
        checksum_sha256=entry.get("SHA256"),
        tags=entry.get("Tag"),
        raw_control=entry,
        repository_id=distribution.repository_id,
        distribution_id=distribution.id,
        component_id=component.id,
        architecture_id=architecture.id,
        last_fetched_at=utcnow(),
    )


async def _get_or_create_component(
    session: AsyncSession,
    distribution: Distribution,
    component_name: str,
) -> Component:
    """Get or create a Component model and link it to the distribution/repository.
    This assumes you're holding the session context manager when you call it.
    """
    result = await session.exec(
        Component.select()
        .where(
            Component.repository_id == distribution.repository_id,
            Component.name == component_name,
        )
        .options(selectinload(Component.distributions))
    )
    component = result.first()

    if component:
        if distribution not in component.distributions:
            component.distributions.append(distribution)
    else:
        component = Component(
            name=component_name, repository_id=distribution.repository_id, distributions=[distribution]
        )

    session.add(component)
    await session.flush()
    return component


async def _get_or_create_architecture(
    session: AsyncSession,
    distribution: Distribution,
    architecture_name: str,
) -> Architecture:
    """Get or create an Architecture model and link it to the distribution/repository.
    This assumes you're holding the session context manager when you call it.
    """
    result = await session.exec(
        Architecture.select()
        .where(
            Architecture.repository_id == distribution.repository_id,
            Architecture.name == architecture_name,
        )
        .options(selectinload(Architecture.distributions))
    )
    architecture = result.one_or_none()

    if architecture:
        if distribution not in architecture.distributions:
            architecture.distributions.append(distribution)
    else:
        architecture = Architecture(
            name=architecture_name,
            repository_id=distribution.repository_id,
            distributions=[distribution],
        )
        session.add(architecture)

    await session.flush([architecture, distribution])
    return architecture


async def _replace_packages_for_target(
    distribution_id: int,
    component_name: str,
    architecture_name: str,
    entries: AsyncIterator[dict],
):
    async with rx.asession() as session:
        session.autoflush = False
        distribution = await session.get_one(Distribution, distribution_id)
        component = await _get_or_create_component(session, distribution, component_name)
        architecture = await _get_or_create_architecture(session, distribution, architecture_name)
        await session.flush()

        query = Package.select().where(
            Package.distribution == distribution,
            Package.component == component,
            Package.architecture == architecture,
        )
        result = await session.exec(query)
        packages: dict[tuple[str, str], Package] = {(pkg.name, pkg.version): pkg for pkg in result.all()}

        idx = 0
        last_update = time.monotonic()
        async for entry in entries:
            idx += 1
            if (name := entry.get("Package")) is None or (version := entry.get("Version")) is None:
                continue

            if package := packages.get((name, version)):
                package.last_fetched_at = utcnow()
            else:
                package = _build_package_model(entry, distribution, component, architecture)

            if package:
                session.add(package)

            if time.monotonic() > last_update + 1:
                await session.flush()
                yield idx
                last_update = time.monotonic()
        else:
            await session.flush()

        distribution.last_fetched_at = utcnow()
        await session.commit()
        yield idx
