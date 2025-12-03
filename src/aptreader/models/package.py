from typing import Annotated

from pydantic import BaseModel, Field

type OptionalStr = str | None
type StrListField = Annotated[list[str], Field(default_factory=list)]


class Package(BaseModel):
    """Represents a package in an APT repository."""

    name: str
    version: str
    architecture: str
    filename: str
    size: int
    sha256: OptionalStr = None
    description: OptionalStr = None
    depends: StrListField
    recommends: StrListField
    suggests: StrListField
    conflicts: StrListField
    section: OptionalStr = None
    priority: OptionalStr = None
    maintainer: OptionalStr = None
    homepage: OptionalStr = None
