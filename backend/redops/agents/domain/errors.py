"""Named domain errors for the RED agent model seam (pure domain)."""

from __future__ import annotations


class AgentModelError(Exception):
    """Base class for agent model seam rule violations."""


class InvalidModelRequestError(AgentModelError, ValueError):
    """A model request is missing a field the seam requires.

    SPEC.md section 6 requires the LLM adapter to log the model, prompt
    version, context references and trace identifiers, and SPEC.md section 9
    requires retrieval to stay within the active client. A request without its
    tenant, model, prompt, prompt version or trace id cannot be attributed to a
    client, versioned, or traced, so it is refused rather than sent.
    """


class InvalidModelUsageError(AgentModelError, ValueError):
    """A token usage figure is negative or not an integer.

    Usage is reported to the operator for spend and trace review (SPEC.md
    section 6), so a negative or untyped count would corrupt that reporting.
    """


class ModelGatewayRuntimeError(AgentModelError, RuntimeError):
    """The live model adapter cannot serve the request in this runtime.

    The fork's provider registry is async while the ``ModelGateway`` port is
    synchronous (SPEC.md section 6: the adapter abstracts the provider). Calling
    the adapter from inside a running event loop would deadlock a synchronous
    bridge, so the adapter refuses with a named error instead of blocking or
    silently dropping the call. The worker/composition layer decides how to
    invoke it, or how to bridge the loop.
    """


class InvalidModelResponseError(AgentModelError, ValueError):
    """A model response is incomplete.

    A response without text or without a typed usage figure cannot be handed to
    an agent use case as a model result, so it is refused rather than presented
    as a completion.
    """
