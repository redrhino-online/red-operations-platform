"""Live RED LLM adapter over the fork provider registry (queue Q2).

SPEC.md section 6: an LLM adapter abstracts model choice and logs model, prompt
version, context references, usage and trace identifiers without storing
secrets. SPEC.md section 13 condition 5: the real OpenRouter path is proven
separately from the deterministic fake that drives the end-to-end path.

``ForkProviderModelGateway`` wraps the fork's provider registry
(``openexecutive.providers``) behind the RED ``ModelGateway`` port: it translates
a typed ``ModelRequest`` into an Anthropic-shaped call, runs it through the
provider the registry selects for the request's model, and translates the
provider's message back into a ``ModelResponse`` that preserves the request's
attribution. The fork's registry is async while the port is synchronous, so the
adapter runs the call through an injected runner (``asyncio.run`` by default)
and refuses rather than deadlocks inside a running event loop.

``LoggingModelGateway`` is a decorator over any ``ModelGateway`` that records
that attribution as a structured log record for spend and trace review. It
never logs the prompt or response text, so client material and any secret that
slipped past validation cannot reach the operational log (SPEC.md section 9).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from redops.agents.application.ports import ModelGateway
from redops.agents.domain.errors import (
    AgentModelError,
    ModelGatewayRuntimeError,
)
from redops.agents.domain.value_objects import (
    ModelRequest,
    ModelResponse,
    ModelUsage,
)

LOGGER_NAME = "redops.agents.model"

DEFAULT_MAX_TOKENS = 1024


class _Provider(Protocol):
    def messages_create(self, **kwargs: Any) -> Awaitable[Any]: ...


ProviderLookup = Callable[[str], Any]
Runner = Callable[[Awaitable[Any]], Any]


def _run_sync(coro: Awaitable[Any]) -> Any:
    """Run the fork provider's coroutine from synchronous code.

    ``asyncio.run`` is correct when the adapter is called from a worker or
    test. Inside a running loop it would raise, so the guard closes the
    coroutine and raises a named error so the caller can bridge the loop or
    call the async provider directly instead of blocking.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    close = getattr(coro, "close", None)
    if close is not None:
        close()
    raise ModelGatewayRuntimeError(
        "the live model adapter cannot run inside a running event loop; "
        "inject a runner or call the async provider directly"
    )


def _extract_text(message: Any) -> str:
    blocks = getattr(message, "content", None) or ()
    parts: list[str] = []
    for block in blocks:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text:
            parts.append(text)
    return "".join(parts)


def _token_count(usage: Any, name: str) -> int:
    value = getattr(usage, name, 0)
    return 0 if value is None else value


class ForkProviderModelGateway(ModelGateway):
    """The live model gateway backed by the fork's provider registry."""

    def __init__(
        self,
        provider_for: ProviderLookup,
        *,
        runner: Runner | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        if not callable(provider_for):
            raise AgentModelError("the live model adapter needs a provider lookup")
        self._provider_for = provider_for
        self._runner = runner or _run_sync
        self._max_tokens = max_tokens

    @property
    def provider_for(self) -> ProviderLookup:
        """The provider lookup this adapter uses, for composition and tests."""
        return self._provider_for

    @classmethod
    def from_fork_registry(cls, **kwargs: Any) -> "ForkProviderModelGateway":
        """Build the adapter over the fork's ``get_provider(model)`` registry.

        The import is lazy so the RED agent package does not hard-depend on the
        fork at import time; the composition layer chooses this adapter for the
        live path (SPEC.md section 6, DoD condition 5).
        """
        from openexecutive.providers.registry import get_provider

        return cls(get_provider, **kwargs)

    def generate(self, request: ModelRequest) -> ModelResponse:
        provider = self._provider_for(request.model)
        create = getattr(provider, "messages_create", None)
        if not callable(create):
            raise AgentModelError(
                f"the provider for model {request.model!r} cannot create "
                "messages"
            )
        message = self._runner(
            create(
                model=request.model,
                max_tokens=self._max_tokens,
                messages=[{"role": "user", "content": request.prompt}],
            )
        )
        usage = getattr(message, "usage", None)
        return ModelResponse(
            text=_extract_text(message),
            model=request.model,
            prompt_version=request.prompt_version,
            usage=ModelUsage(
                input_tokens=_token_count(usage, "input_tokens"),
                output_tokens=_token_count(usage, "output_tokens"),
            ),
            trace_id=request.trace_id,
            context_references=request.context_references,
        )


class LoggingModelGateway(ModelGateway):
    """Decorator that logs the attribution of every model call.

    Satisfies SPEC.md section 6's logging requirement for any backend: the fake
    used offline and the live fork adapter in production both get the same
    structured record without a second implementation. Prompt and response
    text are deliberately excluded (SPEC.md section 9).
    """

    def __init__(
        self, delegate: ModelGateway, *, logger: logging.Logger | None = None
    ) -> None:
        if not isinstance(delegate, ModelGateway):
            raise AgentModelError(
                "the logging model gateway must wrap a ModelGateway"
            )
        self._delegate = delegate
        self._logger = logger or logging.getLogger(LOGGER_NAME)

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    def generate(self, request: ModelRequest) -> ModelResponse:
        response = self._delegate.generate(request)
        self._logger.info(
            "model call",
            extra={
                "redops_tenant": request.tenant_id,
                "redops_model": response.model,
                "redops_prompt_version": response.prompt_version,
                "redops_trace_id": response.trace_id,
                "redops_context_references": list(response.context_references),
                "redops_input_tokens": response.usage.input_tokens,
                "redops_output_tokens": response.usage.output_tokens,
            },
        )
        return response
