"""Reference adapter for the ``MethodVersionRepository`` port (SPEC.md section 6).

The process-local adapter exercises the port contract and the application seam
without a database, so the immutability rule (an approved method version cannot
be re-stated with different content) is testable and the durable PostgreSQL
adapter can follow the same contract. It is not a durable store: a deployment
that needs method versions to survive a restart replaces it at the composition
root.
"""

from __future__ import annotations

from redops.contexts.method.application.ports import MethodVersionRepository
from redops.contexts.method.domain.entities import MethodVersion
from redops.contexts.method.domain.errors import (
    MethodApprovalError,
    MethodVersionConflictError,
    MethodVersionTenantBoundaryError,
)
from redops.contexts.method.domain.value_objects import SemanticVersion


def _require_method_tenant(value: str, operation: str) -> None:
    """Refuse an unscoped read or write of a client's approved method.

    SPEC.md sections 3 and 9 make a method version a client resource that must
    carry its tenant on every command and query; storing or resolving one
    without a client would either leak across clients or create an orphaned
    record.
    """

    if not value or not value.strip():
        raise MethodVersionTenantBoundaryError(
            f"a tenant-scoped method version {operation} requires a non-blank "
            "tenant id; an approved method is a client resource and cannot be "
            "stored or read unscoped"
        )


class InMemoryMethodVersionRepository(MethodVersionRepository):
    """Append-only, process-local approved method store keyed by client and version."""

    def __init__(self) -> None:
        self._methods: dict[tuple[str, str, SemanticVersion], MethodVersion] = {}

    def get(
        self,
        tenant_id: str,
        method_id: str,
        version: SemanticVersion,
    ) -> MethodVersion | None:
        _require_method_tenant(tenant_id, "read")
        return self._methods.get((tenant_id, method_id, version))

    def save(self, method: MethodVersion) -> None:
        _require_method_tenant(method.tenant_id, "write")
        if method.approval is None:
            raise MethodApprovalError(
                "an approved method version store only holds approved methods; "
                "an unapproved draft cannot be stored"
            )
        key = (method.tenant_id, method.method_id, method.semantic_version)
        existing = self._methods.get(key)
        if existing is not None and existing != method:
            raise MethodVersionConflictError(
                f"approved method {method.method_id!r} at version "
                f"{method.semantic_version} is already stored for tenant "
                f"{method.tenant_id!r} with different content; an approved "
                "version is immutable and a change must advance the version"
            )
        self._methods[key] = method

    def close(self) -> None:
        """A process-local store owns no external resource to release."""

        return None
