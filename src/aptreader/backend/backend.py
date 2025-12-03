from datetime import datetime
from functools import partial
from typing import Sequence

import reflex as rx
import sqlmodel as sm
from sqlmodel import JSON, DateTime, Field, Relationship, select, update

update_ts_column = partial(sm.Column, "update_ts", DateTime(timezone=True), server_default=sm.func.now())


class Repository(rx.Model, table=True):
    """The apt repository model."""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    url: str = Field(index=True, unique=True)
    update_ts: DateTime | None = Field(default=None, sa_column=update_ts_column())

    distributions: list["Distribution"] = Relationship(back_populates="repository", cascade_delete=True)


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
    repository: Repository = Relationship(back_populates="distributions")


class State(rx.State):
    """The backend state."""

    repositories: Sequence[Repository] = []
    sort_value: str = ""
    sort_reverse: bool = False
    search_value: str = ""
    current_repo: Repository | None = None

    _first_load: bool = True

    @rx.event
    def load_repositories(self, toast: bool = False) -> rx.event.EventSpec:
        """Load repository entries from the database."""
        try:
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
        repo_url = form_data.get("url")
        if not repo_url:
            return rx.window_alert("Repository URL is required.")
        repo_name = form_data.get("name", None)
        if not repo_name:
            repo_name = repo_url.replace("http://", "").replace("https://", "").replace("/", "_")
            form_data["name"] = repo_name

        with rx.session() as session:
            if existing := session.exec(select(Repository).where(Repository.url == repo_url)).first():
                return rx.window_alert(f"Repository with URL '{repo_url}' already exists: {existing.name}")
            self.current_repo = Repository.model_validate(form_data)
            session.add(self.current_repo)
            session.commit()
            session.refresh(self.current_repo)
        self.load_repositories(False)
        return rx.toast.info(f"Repository '{form_data.get('name')}' added successfully.")

    @rx.event
    def update_repository_in_db(self, form_data: dict):
        """Update the repository's update timestamp to the current time."""
        if self.current_repo is None:
            return rx.toast.error("No current repository selected.")

        # prevent attempts to change the primary key
        form_data.pop("id", None)

        with rx.session() as session:
            repo = session.get(Repository, self.current_repo.id, populate_existing=True, with_for_update=True)
            if not repo:
                return rx.window_alert("Repository not found in the database.")
            repo.sqlmodel_update(form_data)
            # let the database set the update timestamp
            repo.update_ts = None
            session.add(repo)
            session.commit()
            session.refresh(repo)

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
        return rx.toast.info(f"Repository '{repo.name}' deleted successfully.")
