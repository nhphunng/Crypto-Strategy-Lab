from __future__ import annotations

import re
from dataclasses import dataclass

_SEMVER = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)\Z")


@dataclass(frozen=True, order=True, slots=True)
class SemanticVersion:
    major: int
    minor: int
    patch: int

    def __post_init__(self) -> None:
        if min(self.major, self.minor, self.patch) < 0:
            raise ValueError("semantic version components must be non-negative")

    @classmethod
    def parse(cls, value: str) -> SemanticVersion:
        match = _SEMVER.fullmatch(value)
        if match is None:
            raise ValueError("version must use strict MAJOR.MINOR.PATCH format")
        return cls(*(int(part) for part in match.groups()))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True, slots=True)
class ContractVersionRange:
    major: int
    minimum_minor: int
    maximum_minor: int

    def __post_init__(self) -> None:
        if self.major < 0 or self.minimum_minor < 0 or self.maximum_minor < self.minimum_minor:
            raise ValueError("invalid supported contract range")

    def supports(self, version: SemanticVersion) -> bool:
        return (
            version.major == self.major
            and self.minimum_minor <= version.minor <= self.maximum_minor
        )
