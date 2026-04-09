import asyncio
import datetime
import logging
from math import floor
from pathlib import Path

import reflex as rx
import sqlmodel as sm
from sqlalchemy.exc import NoResultFound
from sqlmodel import select

from aptreader.constants import UNIX_EPOCH_START
from aptreader.fetcher import discover_distributions, fetch_distributions
from aptreader.models import Distribution, Repository
from aptreader.utils import long_running_task

logger = logging.getLogger(__name__)


class AppState(rx.State):
    """The backend state."""

    repositories: list[Repository] = []
    sort_value: str = ""
    sort_reverse: bool = False
    search_value: str = ""
    current_repo: Repository | None = None
    current_distro: Distribution | None = None

    _first_load: bool = True
    is_loading: bool = False

    is_fetching: bool = False
    fetch_repo_id: int = -1
    fetch_progress: int = 100
    fetch_message: str = ""

    @rx.event
    def load_repositories(self, toast: bool = False):
        """Load repository entries from the database."""
        try:
            self.is_loading = True
            is_first = self._first_load
            self._first_load = False
            with rx.session() as session:
                query = Repository.select()
                if self.search_value:
                    search_value = self.search_value.lower().strip()
                    query = query.where(
                        sm.or_(
                            Repository.name.ilike(search_value),  # type: ignore
                            Repository.url.ilike(search_value),  # type: ignore
                        )
                    )
                if self.sort_value:
                    sort_field = getattr(Repository, self.sort_value)
                    if self.sort_value == "update_ts":
                        order = sm.desc(sort_field) if self.sort_reverse else sm.asc(sort_field)
                    else:
                        order = sm.desc(sort_field) if self.sort_reverse else sm.asc(sort_field)
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
    def sort_values(self, sort_value: str):
        print(f"Sorting by {sort_value}")
        self.sort_value = sort_value
        self.load_repositories(False)

    @rx.event
    def toggle_sort(self):
        print("Toggling sort order")
        self.sort_reverse = not self.sort_reverse
        self.load_repositories(False)

    @rx.event
    def filter_values(self, search_value: str):
        print(f"Filtering by {search_value}")
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
                        date=parsed_data.get("Date", UNIX_EPOCH_START),
                        description=parsed_data.get("Description"),
                        origin=parsed_data.get("Origin", ""),
                        suite=parsed_data.get("Suite", dist_name),
                        version=parsed_data.get("Version", ""),
                        codename=parsed_data.get("Codename", dist_name),
                        repository_id=repo_id,
                        last_fetched_at=datetime.datetime.fromtimestamp(0, tz=datetime.UTC),
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

    @rx.var
    def repository_names(self) -> list[str]:
        """Get the list of repository names."""
        return [repo.name for repo in self.repositories]
