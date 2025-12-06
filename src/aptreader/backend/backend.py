import asyncio
import logging
from math import floor
from pathlib import Path
from typing import Any, AsyncIterator

import reflex as rx
import sqlmodel as sm
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from aptreader.fetcher import (
    discover_distributions,
    download_packages_index,
    fetch_distributions,
    iter_packages_entries_async,
)
from aptreader.models.packages import Architecture, Component, Package
from aptreader.models.repository import Distribution, Repository
from aptreader.utils import long_running_task

logger = logging.getLogger(__name__)


def _safe_int(value: str | None) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _clean_text(value: str | None) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else value or None


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
        description=_clean_text(entry.get("Description")),
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
    )


class AppState(rx.State):
    """The backend state."""

    repositories: list[Repository] = []
    sort_value: str = ""
    sort_reverse: bool = False
    search_value: str = ""
    current_repo: Repository | None = None

    _first_load: bool = True
    is_loading: bool = False

    is_fetching: bool = False
    fetch_repo_id: int = -1
    fetch_progress: int = 100
    fetch_message: str = ""

    is_fetching_packages: bool = False
    package_fetch_distribution_id: int = -1
    package_fetch_progress: int = 100
    package_fetch_message: str = ""

    @rx.event
    def repo_distribution_count(self, repo_id: int) -> int:
        """Get the number of distributions for the current repository."""
        with rx.session() as session:
            count = session.exec(
                select(func.count()).select_from(Distribution).where(Distribution.repository_id == repo_id)
            ).one()
            if count is not None:
                return count
        return 0

    @rx.event
    def load_repositories(self, toast: bool = False):
        """Load repository entries from the database."""
        try:
            self.is_loading = True
            is_first = self._first_load
            self._first_load = False
            with rx.session() as session:
                query = select(Repository)
                if self.search_value:
                    search_value = f"%{str(self.search_value).lower().strip()}%"
                    query = query.where(
                        sm.or_(
                            *[
                                getattr(Repository, field).ilike(search_value)
                                for field in Repository.model_fields.keys()
                                if field in ["name", "url"]
                            ],
                        )
                    )
                if self.sort_value:
                    sort_field = getattr(Repository, self.sort_value)
                    if self.sort_value == "update_ts":
                        order = sm.desc(sort_field) if self.sort_reverse else sm.asc(sort_field)
                    else:
                        order = (
                            sm.desc(sm.func.lower(sort_field))
                            if self.sort_reverse
                            else sm.asc(sm.func.lower(sort_field))
                        )
                    query = query.order_by(order)

                self.repositories = list(session.exec(query).all())

            return rx.toast.success("Repositories loaded successfully.") if (toast or is_first) else rx.noop()
        except Exception as e:
            return rx.toast.error(f"Error loading repositories: {e}")
        finally:
            self.is_loading = False

    @rx.event
    def set_current_repo(self, repo: Repository):
        self.current_repo = repo

    @rx.event
    def set_current_repo_id(self, repo_id: int | None):
        """Set the current repository by ID."""
        if repo_id:
            with rx.session() as session:
                self.current_repo = session.get(Repository, repo_id)
        else:
            logger.info("Clearing current repository (no ID provided)")
            self.current_repo = None

    @rx.event
    def set_current_repo_name(self, repo_name: str):
        """Set the current repository by name."""
        repo = next((r for r in self.repositories if r.name == repo_name), None)
        if repo:
            self.set_current_repo(repo)

    @rx.event
    def sort_values(self, sort_value: str):
        self.sort_value = sort_value
        self.load_repositories(False)

    @rx.event
    def toggle_sort(self):
        self.sort_reverse = not self.sort_reverse
        self.load_repositories(False)

    @rx.event
    def filter_values(self, search_value: str):
        self.search_value = search_value
        self.load_repositories(False)

    @rx.event
    def add_repository_to_db(self, form_data: dict) -> rx.event.EventSpec:
        """Add a new repository."""
        try:
            repo_url = form_data.get("url")
            if not repo_url:
                return rx.window_alert("Repository URL is required.")
            repo_name = form_data.get("name", None)
            if not repo_name:
                repo_name = repo_url.replace("http://", "").replace("https://", "").replace("/", "_")
                form_data["name"] = repo_name

            with rx.session() as session:
                if existing := session.exec(select(Repository).where(Repository.url == repo_url)).first():
                    return rx.window_alert(
                        f"Repository with URL '{repo_url}' already exists: {existing.name}"
                    )
                self.current_repo = Repository.model_validate(form_data)
                session.add(self.current_repo)
                session.commit()
                session.refresh(self.current_repo)
            self.load_repositories(False)

            return rx.toast.success(f"Repository '{form_data.get('name')}' added successfully.")
        except Exception as e:
            return rx.window_alert(f"Error adding repository: {e}")

    @rx.event
    def update_repository_in_db(self, form_data: dict):
        """Update the repository's fields."""
        if self.current_repo is None:
            return rx.toast.error("No current repository selected.")

        # prevent attempts to change the primary key
        form_data.pop("id", None)

        with rx.session() as session:
            repo = session.get(Repository, self.current_repo.id, with_for_update=True)
            if not repo:
                return rx.window_alert("Repository not found in the database.")
            repo.sqlmodel_update(form_data)
            session.add(repo)
            session.commit()
            session.refresh(repo)

        self.load_repositories(False)
        return rx.toast.success(f"Repository '{form_data.get('name')}' updated successfully.")

    @rx.event
    def delete_repository_from_db(self, id: int | None) -> rx.event.EventSpec:
        """Delete a repository by ID."""
        if id is None:
            return rx.window_alert("No repository ID provided for deletion.")

        with rx.session() as session:
            repo = session.get(Repository, id)
            if not repo:
                return rx.window_alert(f"Can't delete repository ID {id} - not found in database.")
            session.delete(repo)
            session.commit()
        if self.current_repo and self.current_repo.id == id:
            self.current_repo = None

        self.load_repositories(False)
        return rx.toast.success(f"Repository '{repo.name}' deleted successfully.")

    @long_running_task
    @rx.event(background=True)
    async def fetch_repository_distributions(self, repo_id: int):
        """Discover and fetch distributions for a repository.

        Args:
            repo_id: The repository ID to fetch distributions for
        """
        # Get the repository from the database
        async with self:
            self.set_current_repo_id(repo_id)
            if not self.current_repo or not self.current_repo.id:
                yield rx.toast.error("Repository not found.")
                return
            repo_id = self.current_repo.id
            repo_name = self.current_repo.name
            repo_url = self.current_repo.url

        try:
            async with self:
                self.fetch_repo_id = repo_id
                self.fetch_progress = 0
                self.fetch_message = f"Starting distribution discovery for {repo_name}..."
                self.is_fetching = True
            await asyncio.sleep(0)

            distributions = await discover_distributions(repo_url)
            if not distributions:
                yield rx.toast.warning(f"No distributions found for {repo_name}")
                return

            num_dists = len(distributions)
            async with self:
                self.fetch_message = f"Discovered {num_dists} distributions, starting fetch..."
            await asyncio.sleep(0)

            # Fetch distributions
            idx = 0
            results: list[tuple[str, Path, dict]] = []
            async for dist_info in fetch_distributions(repo_url, distributions):
                results.append(dist_info)
                idx += 1
                async with self:
                    self.fetch_progress = floor((idx / num_dists) * 100)
                    self.fetch_message = f"Fetched distribution {idx}/{num_dists}: {dist_info[0]}"
                await asyncio.sleep(0)

            # Save distributions to database
            await self._replace_repository_distributions(repo_id, results)

            # Reload repositories to show updated timestamp
            async with self:
                self.fetch_message = "Fetch complete."
            yield rx.toast.success(f"Successfully fetched {len(results)} distributions for {repo_name}")

        except Exception as e:
            logger.exception("Error fetching distributions:")
            yield rx.toast.error(f"Error fetching distributions: {e}")
        finally:
            async with self:
                self.fetch_progress = 100
            await asyncio.sleep(5)
            async with self:
                self.is_fetching = False
                self.fetch_progress = 100
                self.fetch_message = ""
                self.fetch_repo_id = -1
            await asyncio.sleep(0)

    async def _replace_repository_distributions(
        self,
        repo_id: int,
        distributions: list[tuple[str, Path, dict]],
    ):
        """Update the distributions for a repository.

        Args:
            repo_id: The repository ID
            distributions: List of Distribution objects to add/update
        """

        try:
            async with rx.asession() as session:
                repo = await session.get_one(Repository, repo_id, with_for_update=True)
                if not repo:
                    return rx.toast.error("Repository not found in database during save.")

                # Delete existing distributions
                existing_dists = await session.exec(
                    select(Distribution).where(Distribution.repository_id == repo_id)
                )
                for dist in existing_dists.all():
                    await session.delete(dist)
                await session.flush()

                # Add new distributions
                new_dists = [
                    Distribution(
                        name=dist_name,
                        raw=local_path.read_text(encoding="utf-8"),
                        architecture_names=parsed_data.get("Architectures", "").split(),
                        component_names=parsed_data.get("Components", "").split(),
                        date=parsed_data.get("Date"),
                        description=parsed_data.get("Description"),
                        origin=parsed_data.get("Origin", ""),
                        suite=parsed_data.get("Suite", dist_name),
                        version=parsed_data.get("Version", ""),
                        codename=parsed_data.get("Codename", dist_name),
                        repository_id=repo_id,
                    )
                    for dist_name, local_path, parsed_data in distributions
                ]
                session.add_all(new_dists)

                await session.commit()
                return rx.toast.success(f"Distributions saved for repository '{repo.name}'")
        except NoResultFound:
            logger.exception(f"Could not find repository {repo_id}", stacklevel=2)
            return rx.toast.error(f"Could not find repository with ID {repo_id}")
        except Exception as e:
            logger.exception("Error saving distributions to database:", stacklevel=2)
            return rx.toast.error(f"Error saving distributions to database: {e}")

    @long_running_task
    @rx.event(background=True)
    async def fetch_distribution_packages(self, distribution_id: int | None):
        """Download and persist Packages indexes for a distribution."""
        if distribution_id is None:
            logger.error("No distribution ID provided.")
            yield rx.toast.error("No distribution ID provided.")
            return

        async with rx.asession() as session:
            distribution = await session.get_one(Distribution, distribution_id)
            repository = distribution.repository
            if not repository:
                yield rx.toast.error(
                    f"Distribution #{distribution_id} has no associated repository.", duration=10000
                )
                return
            repo_url = repository.url
            name = distribution.name
            codename = distribution.codename or name
            component_names = distribution.component_names or []
            architecture_names = distribution.architecture_names or []

        if not component_names or not architecture_names:
            logger.warning("Distribution missing components or architectures.")
            yield rx.toast.warning("Distribution metadata missing components/architectures.")
            return

        async with self:
            targets = [(comp, arch) for comp in component_names for arch in architecture_names]
            total_targets = len(targets)
            self.package_fetch_distribution_id = distribution_id
            self.package_fetch_progress = 0
            self.package_fetch_message = f"Preparing package sync for {name}"
            self.is_fetching_packages = True
        await asyncio.sleep(0)

        total_packages = 0
        processed = 0
        try:
            for comp_name, arch_name in targets:
                async with self:
                    self.package_fetch_message = f"Downloading {name} {comp_name}/{arch_name}"
                    await asyncio.sleep(0)

                download_result = await download_packages_index(repo_url, name, comp_name, arch_name)
                if not download_result:
                    logger.info(f"No Packages file for {comp_name}/{arch_name}")
                    processed += 1
                    async with self:
                        self.package_fetch_progress = floor((processed / total_targets) * 100)
                    await asyncio.sleep(0)
                    continue

                _, local_path = download_result
                try:
                    new_count = 0
                    async for count in self._replace_packages_for_target(
                        distribution_id,
                        comp_name,
                        arch_name,
                        iter_packages_entries_async(local_path),
                    ):
                        async with self:
                            self.package_fetch_message = (
                                f"Imported {count} new packages for {comp_name}/{arch_name}"
                            )
                        new_count = count
                        await asyncio.sleep(0)
                    total_packages += new_count
                except Exception as write_error:  # pragma: no cover - defensive logging
                    logger.exception("Failed to save packages for %s/%s", comp_name, arch_name)
                    async with self:
                        self.package_fetch_message = f"Error saving {comp_name}/{arch_name}: {write_error}"
                    yield rx.toast.error(f"Error saving packages for {comp_name}/{arch_name}: {write_error}")
                    continue

                processed += 1
                async with self:
                    self.package_fetch_progress = floor((processed / total_targets) * 100)
                    self.package_fetch_message = f"Imported {new_count} packages for {comp_name}/{arch_name}"
                await asyncio.sleep(0)

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
                self.is_fetching_packages = False
                self.package_fetch_distribution_id = -1
                self.package_fetch_progress = 100
                self.package_fetch_message = ""
            await asyncio.sleep(0)

    async def _get_or_create_component(
        self,
        session: AsyncSession,
        distribution: Distribution,
        component_name: str,
    ) -> Component:
        """Get or create a Component model and link it to the distribution/repository.
        This assumes you're holding the session context manager when you call it.
        """
        component = await session.scalar(
            select(Component).where(
                Component.repository_id == distribution.repository_id,
                Component.name == component_name,
            )
        )
        if component:
            if distribution not in component.distributions:
                component.distributions.append(distribution)
        else:
            component = Component(
                name=component_name, repository_id=distribution.repository_id, distributions=[distribution]
            )
            session.add(component)

        await session.flush([component, distribution])
        return component

    async def _get_or_create_architecture(
        self,
        session: AsyncSession,
        distribution: Distribution,
        architecture_name: str,
    ) -> Architecture:
        """Get or create an Architecture model and link it to the distribution/repository.
        This assumes you're holding the session context manager when you call it.
        """
        architecture = await session.scalar(
            select(Architecture).where(
                Architecture.repository_id == distribution.repository_id,
                Architecture.name == architecture_name,
            )
        )
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
        self,
        distribution_id: int,
        component_name: str,
        architecture_name: str,
        entries: AsyncIterator[dict],
    ):
        async with rx.asession() as session:
            distribution = await session.get_one(Distribution, distribution_id)
            component = await self._get_or_create_component(session, distribution, component_name)
            architecture = await self._get_or_create_architecture(session, distribution, architecture_name)
            await session.flush()

            idx = 0
            new_count = 0
            async for entry in entries:
                package = _build_package_model(entry, distribution, component, architecture)
                idx += 1
                if not package:
                    continue

                session.add(package)
                new_count += 1
                if idx % 10 == 0:
                    await session.flush()
                    yield new_count

            await session.commit()
            yield new_count

    @rx.var(cache=True)
    def distributions(self) -> list[Distribution]:
        """Get the distributions for the current repository."""
        if self.current_repo is None:
            return []
        with rx.session() as session:
            repo = session.get(Repository, self.current_repo.id, populate_existing=True)
            if not repo:
                return []
            return repo.distributions

    @rx.var
    def current_repo_id(self) -> int:
        """Get the current repository name."""
        return self.current_repo.id if self.current_repo and self.current_repo.id else -1

    @rx.var
    def current_repo_name(self) -> str:
        """Get the current repository name."""
        return self.current_repo.name if self.current_repo else "Unknown"

    @rx.var
    def repository_names(self) -> list[str]:
        """Get the list of repository names."""
        return [repo.name for repo in self.repositories]
