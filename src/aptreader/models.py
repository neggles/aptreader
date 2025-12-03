"""Data models for APT repository structures."""

from pydantic import Field, BaseModel
from pydantic.dataclasses import dataclass


class Package(BaseModel):
    """Represents a package in an APT repository."""

    name: str
    version: str
    architecture: str
    filename: str
    size: int
    sha256: str | None = None
    description: str | None = None
    depends: list[str] = Field(default_factory=list)
    recommends: list[str] = Field(default_factory=list)
    suggests: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    section: str | None = None
    priority: str | None = None
    maintainer: str | None = None
    homepage: str | None = None


class Component(BaseModel):
    """Represents a component (e.g., main, universe) in a distribution."""

    name: str
    packages: dict[str, Package] = Field(default_factory=dict)


class Release(BaseModel):
    """Represents a release/distribution (e.g., jammy, focal) in an APT repository."""

    name: str
    codename: str | None = None
    suite: str | None = None
    version: str | None = None
    architectures: list[str] = Field(default_factory=list)
    components: dict[str, Component] = Field(default_factory=dict)


class Repository(BaseModel):
    """Represents an APT repository."""

    url: str
    name: str
    releases: dict[str, Release] = Field(default_factory=dict)
