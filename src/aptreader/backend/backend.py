import reflex as rx
from sqlmodel import Field


class Repository(rx.Model, table=True):
    """Repository model representing an APT repository."""

    url: str
    name: str


class Settings(rx.Model, table=True):
    """Settings model for application configuration."""

    id: int | None = Field(default=None, primary_key=True)
    cache_dir: str
