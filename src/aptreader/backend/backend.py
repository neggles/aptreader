from datetime import UTC, datetime
from importlib.metadata import distribution
from pathlib import Path
from typing import Annotated, ClassVar, Sequence

import reflex as rx
import sqlalchemy as sa
import sqlmodel as sm
from pydantic import computed_field
from sqlalchemy.orm.session import object_session
from sqlmodel import JSON, DateTime, Field, Relationship, func, select

from ..fetcher import discover_distributions, fetch_distributions


class Distribution(rx.Model, table=True):
    id: int | None = Field(default=None, primary_key=True)
    raw: str | None = Field(default=None)
    architectures: list[str] = Field(sa_type=JSON, default_factory=list)
    components: list[str] = Field(sa_type=JSON, default_factory=list)
    date: str | None = Field(default=None)
    description: str | None = Field(default=None)
    origin: str
    suite: str
    version: str
    codename: str

    repository_id: int = Field(default=None, foreign_key="repository.id", ondelete="CASCADE")
    repository: "Repository" = Relationship(back_populates="distributions")


class Repository(rx.Model, table=True):
    """The apt repository model."""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    url: str = Field(index=True, unique=True)
    update_ts: datetime = Field(
        default=datetime.now(tz=UTC),
        sa_column=sm.Column(
            "update_ts",
            DateTime(timezone=True),
            server_default=sm.func.now(),
            onupdate=sm.func.now(),
            nullable=False,
        ),
    )

    distributions: list["Distribution"] = Relationship(back_populates="repository", cascade_delete=True)

    @computed_field
    @property
    def distribution_count(self) -> int:
        """Get the number of distributions for this repository."""
        with rx.session() as session:
            q = select(func.count()).select_from(Distribution).where(Distribution.repository_id == self.id)
            count = session.exec(q).one_or_none()
            return count if count is not None else 0
        return 0


class State(rx.State):
    """The backend state."""

    repositories: Sequence[Repository] = []
    sort_value: str = ""
    sort_reverse: bool = False
    search_value: str = ""
    current_repo: Repository | None = None

    _first_load: bool = True
    is_loading: bool = False

    is_fetching: bool = False
    fetch_progress: str = ""
    distributions: list[Distribution] = []

    @rx.event
    def distribution_count(self, repo_id: int) -> int:
        """Get the number of distributions for the current repository."""
        with rx.session() as session:
            count = session.exec(
                select(func.count()).select_from(Distribution).where(Distribution.repository_id == repo_id)
            ).one()
            if count is not None:
                return count
        return 0

    @rx.event
    def load_repositories(self, toast: bool = False) -> rx.event.EventSpec:
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

                self.repositories = session.exec(query).all()

            return rx.toast.success("Repositories loaded successfully.") if (toast or is_first) else rx.noop()
        except Exception as e:
            return rx.toast.error(f"Error loading repositories: {e}")
        finally:
            self.is_loading = False

    @rx.event
    def set_current_repo(self, repo_id: int | None):
        """Set the current repository by ID."""
        with rx.session() as session:
            self.current_repo = session.get(Repository, repo_id, populate_existing=True) if repo_id else None

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
    def get_repository(self, repo: Repository):
        self.current_repo = repo

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
            repo = session.get(Repository, self.current_repo.id, populate_existing=True, with_for_update=True)
            if not repo:
                return rx.window_alert("Repository not found in the database.")
            repo.sqlmodel_update(form_data)
            session.add(repo)
            session.commit()
            session.refresh(repo)

        self.load_repositories(False)
        return rx.toast.success(f"Repository '{form_data.get('name')}' updated successfully.")

    @rx.event
    def delete_repository(self, id: int | None) -> rx.event.EventSpec:
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

    @rx.event
    def update_fetch_progress(self, message: str):
        """Update the fetch progress message."""
        self.fetch_progress = message

    @rx.event(background=True)
    async def fetch_repository_distributions(self, repo_id: int):
        """Discover and fetch distributions for a repository.

        Args:
            repo_id: The repository ID to fetch distributions for
        """
        # Get the repository from the database
        async with self:
            self.set_current_repo(repo_id)
            if not self.current_repo or not self.current_repo.id:
                yield rx.toast.error("Repository not found.")
                return
            repo_id = self.current_repo.id
            repo_name = self.current_repo.name
            repo_url = self.current_repo.url

        try:
            async with self:
                self.is_fetching = True
                self.fetch_progress = f"Starting distribution discovery for {repo_name}..."
            yield

            distributions = await discover_distributions(repo_url)
            if not distributions:
                yield rx.toast.warning(f"No distributions found for {repo_name}")
                return
            num_dists = len(distributions)
            async with self:
                self.fetch_progress = f"Discovered {num_dists} distributions, starting fetch..."
                yield

            # Fetch distributions
            idx = 0
            results: list[tuple[str, Path, dict]] = []
            async for dist_info in fetch_distributions(repo_url, distributions):
                results.append(dist_info)
                idx += 1
                async with self:
                    self.fetch_progress = f"Fetched distribution {idx}/{num_dists}: {dist_info[0]}"
                yield

            # Save distributions to database
            async with self:
                self.fetch_progress = f"Saving {len(results)} distributions to database..."
            yield

            await self.replace_repository_distributions(repo_id, results)

            # Reload repositories to show updated timestamp
            async with self:
                self.load_repositories(False)
            yield rx.toast.success(f"Successfully fetched {len(results)} distributions for {repo_name}")

        except Exception as e:
            yield rx.toast.error(f"Error fetching distributions: {str(e)}")
        finally:
            async with self:
                self.is_fetching = False
                self.fetch_progress = ""
            yield

    @rx.event
    async def replace_repository_distributions(
        self, repo_id: int, distributions: list[tuple[str, Path, dict]]
    ):
        """Update the distributions for a repository.

        Args:
            repo_id: The repository ID
            distributions: List of Distribution objects to add/update
        """

        with rx.session() as session:
            repo = session.get(Repository, repo_id, populate_existing=True, with_for_update=True)
            if not repo:
                yield rx.toast.error("Repository not found in database during save.")
                return
            try:
                # Delete existing distributions for this repo
                for dist in repo.distributions:
                    session.delete(dist)

                # Add new distributions
                for dist_name, local_path, parsed_data in distributions:
                    # Extract data from parsed Release file
                    architectures = parsed_data.get("Architectures", "").split()
                    components = parsed_data.get("Components", "").split()

                    dist = Distribution(
                        raw=local_path.read_text(encoding="utf-8"),
                        architectures=architectures,
                        components=components,
                        date=parsed_data.get("Date"),
                        description=parsed_data.get("Description"),
                        origin=parsed_data.get("Origin", ""),
                        suite=parsed_data.get("Suite", dist_name),
                        version=parsed_data.get("Version", ""),
                        codename=parsed_data.get("Codename", dist_name),
                        repository_id=repo_id,
                    )
                    session.add(dist)

                # Update repository timestamp
                session.add(repo)
                session.commit()
            except Exception as e:
                yield rx.window_alert(f"Error saving distributions to database: {e}")
                return

        yield rx.toast.success(f"Distributions updated for repository '{repo.name}'")
