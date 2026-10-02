"""Change impact policy for the Method bounded context (pure domain).

SPEC.md section 4: changing an approved upstream method emits an impact
assessment; dependent offers, briefs, assets, journeys and claims are marked
review required with human owners and due dates. SPEC.md section 11 requires
that changing a method version identifies dependents.
"""

from __future__ import annotations

from datetime import date
from typing import Iterable

from redops.contexts.method.domain.entities import MethodVersion
from redops.contexts.method.domain.errors import (
    InvalidMethodVersionError,
    MethodChangeImpactError,
)
from redops.contexts.method.domain.value_objects import (
    ChangeSeverity,
    DependentArtifact,
    ImpactAssessment,
    ReviewRequirement,
)


class MethodChangeImpactPolicy:
    """Builds the review queue a change to an approved method requires."""

    def assess(
        self,
        previous: MethodVersion,
        current: MethodVersion,
        dependents: Iterable[DependentArtifact],
        *,
        due_on: date | None = None,
        reason: str = "upstream method version changed",
    ) -> ImpactAssessment:
        """Emit an impact assessment for a newer version of an approved method.

        Only a change to an approved method has downstream effects, and the new
        version must advance the semantic version. Every dependent is marked
        review required with its named human owner and a due date, so a change
        produces an owned queue rather than silent invalidation. The previous
        approved MethodVersion is left untouched.
        """
        if previous.method_id != current.method_id:
            raise MethodChangeImpactError(
                "change impact requires two versions of the same method"
            )
        if previous.tenant_id != current.tenant_id:
            raise MethodChangeImpactError(
                "change impact cannot cross tenant boundaries"
            )
        if not previous.is_approved:
            raise MethodChangeImpactError(
                "only a change to an approved method emits an impact assessment"
            )

        try:
            severity: ChangeSeverity = current.semantic_version.change_from(
                previous.semantic_version
            )
        except InvalidMethodVersionError as error:
            raise MethodChangeImpactError(
                "a method change must advance the semantic version"
            ) from error

        requirements = tuple(
            ReviewRequirement(artifact=artifact, due_on=self._due(due_on, artifact), reason=reason)
            for artifact in dependents
        )

        return ImpactAssessment(
            method_id=previous.method_id,
            tenant_id=previous.tenant_id,
            previous_version=previous.semantic_version,
            new_version=current.semantic_version,
            severity=severity,
            requirements=requirements,
        )

    @staticmethod
    def _due(due_on: date | None, artifact: DependentArtifact) -> date:
        if due_on is None:
            raise MethodChangeImpactError(
                f"review requirement for {artifact.artifact_id!r} requires a due date"
            )
        return due_on
