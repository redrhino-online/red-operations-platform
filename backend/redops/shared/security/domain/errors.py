"""Named domain errors for the shared prompt-injection guard.

SPEC.md section 5 says an agent's output is a proposal or an authorized internal
action, never an implicit grant of authority, and section 5 requires tool calls
to be validated outside model output. SPEC.md section 9 treats client material
as confidential. The errors below name the two ways that rule is broken: content
that cannot be admitted as evidence-bearing data, and an action that tries to
derive authority from data instead of from a human or an approved gate.
"""

from __future__ import annotations


class PromptInjectionError(Exception):
    """Base class for prompt-injection guard violations."""


class UntrustedContentError(PromptInjectionError, ValueError):
    """Ingested material was admitted without the identity it requires.

    SPEC.md section 5 makes ingested client material data that must stay
    traceable to its source and client. A chunk missing its client, its source
    reference or its text cannot be cited or scoped, so it is refused on
    admission rather than carried into a model context as anonymous text.
    """


class UntrustedAuthorityError(PromptInjectionError):
    """An action tried to derive authority from data rather than a human.

    SPEC.md section 5 forbids treating ingested client material or model output
    as an implicit grant of authority: a gate cannot be changed and a tool call
    cannot be directed by content that was merely read. Only an operator
    decision or an approved gate confers authority (SPEC.md sections 4 and 5),
    so any other basis is refused.
    """


class InjectionTenantBoundaryError(PromptInjectionError):
    """The guard was used outside the client it is scoped to.

    SPEC.md section 5 limits retrieval to the active client and section 9
    forbids cross-client access. The guard is bound to one active client, so
    admitting material for, or authorizing an action belonging to, a different
    client is refused rather than answered across the boundary.
    """
