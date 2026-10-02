"""Value objects for the Method bounded context (pure domain)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from redops.contexts.method.domain.errors import (
    InvalidMethodError,
    InvalidMethodVersionError,
    MethodApprovalError,
)


class ArtifactKind(Enum):
    """Kinds of artefact that depend on an approved method.

    SPEC.md section 4 names dependent offers, briefs, assets, journeys and
    claims when an approved upstream method changes.
    """

    OFFER = "offer"
    BRIEF = "brief"
    ASSET = "asset"
    JOURNEY = "journey"
    CLAIM = "claim"


class ChangeSeverity(Enum):
    """How disruptive a method change is to its dependents.

    A patch change is editorial; a minor or major change alters the method's
    substance. Governance may apply a lighter approval policy to editorial
    changes if the designated authority matrix allows it (SPEC.md section 4).
    """

    EDITORIAL = "editorial"
    SUBSTANTIVE = "substantive"


@dataclass(frozen=True, order=True)
class SemanticVersion:
    """An exact, ordered method version. Approval pins one of these.

    SPEC.md section 3 requires a MethodVersion to carry a semantic version and
    approval to pin the exact version and intended use.
    """

    major: int
    minor: int
    patch: int

    def __post_init__(self) -> None:
        for label, value in (
            ("major", self.major),
            ("minor", self.minor),
            ("patch", self.patch),
        ):
            if value < 0:
                raise InvalidMethodVersionError(
                    f"semantic version {label} must be >= 0"
                )

    @classmethod
    def parse(cls, text: str) -> "SemanticVersion":
        if not isinstance(text, str):
            raise InvalidMethodVersionError("semantic version must be a string")
        parts = text.split(".")
        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            raise InvalidMethodVersionError(
                f"semantic version must be major.minor.patch, got {text!r}"
            )
        return cls(int(parts[0]), int(parts[1]), int(parts[2]))

    def change_from(self, previous: "SemanticVersion") -> ChangeSeverity:
        """Classify this version relative to an earlier one.

        Rejects an equal or older version: a change must advance the version so
        the previous approved method stays historically identifiable rather than
        being overwritten (SPEC.md section 4).
        """
        if self <= previous:
            raise InvalidMethodVersionError(
                f"a method change must advance the version from {previous} to a "
                f"newer version, got {self}"
            )
        if self.major != previous.major or self.minor != previous.minor:
            return ChangeSeverity.SUBSTANTIVE
        return ChangeSeverity.EDITORIAL

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True)
class MethodApproval:
    """An approval pinned to one exact method version and intended use.

    SPEC.md section 3: "Approval pins an exact version and intended use." An
    approval never authorizes a different version or a different scope.
    """

    version: SemanticVersion
    intended_use: str
    approved_by: str
    approved_on: date

    def __post_init__(self) -> None:
        if not self.intended_use or not self.intended_use.strip():
            raise MethodApprovalError("method approval intended use is required")
        if not self.approved_by or not self.approved_by.strip():
            raise MethodApprovalError("method approval approver is required")

    def authorizes(self, version: SemanticVersion, intended_use: str) -> bool:
        return self.version == version and self.intended_use == intended_use


@dataclass(frozen=True)
class DependentArtifact:
    """An artefact that must be reviewed when its method version changes.

    It names a human owner so a change produces an owned review queue rather
    than silent invalidation (SPEC.md section 4).
    """

    artifact_id: str
    kind: ArtifactKind
    owner: str

    def __post_init__(self) -> None:
        if not self.artifact_id or not self.artifact_id.strip():
            raise InvalidMethodError("dependent artifact id is required")
        if not self.owner or not self.owner.strip():
            raise InvalidMethodError(
                f"dependent artifact {self.artifact_id!r} requires a human owner"
            )


@dataclass(frozen=True)
class ReviewRequirement:
    """One dependent artifact marked review required, with an owner and due date."""

    artifact: DependentArtifact
    due_on: date
    reason: str

    def __post_init__(self) -> None:
        if not self.reason or not self.reason.strip():
            raise InvalidMethodError("review requirement reason is required")


@dataclass(frozen=True)
class ImpactAssessment:
    """The recorded impact of changing an approved method (SPEC.md section 4).

    It names the previous and new exact versions, the change severity, and the
    dependent artifacts marked review required. The previous version's approval
    is untouched, so prior releases stay historically identifiable.
    """

    method_id: str
    tenant_id: str
    previous_version: SemanticVersion
    new_version: SemanticVersion
    severity: ChangeSeverity
    requirements: tuple[ReviewRequirement, ...] = ()

    @property
    def affected_kinds(self) -> frozenset[ArtifactKind]:
        return frozenset(requirement.artifact.kind for requirement in self.requirements)
