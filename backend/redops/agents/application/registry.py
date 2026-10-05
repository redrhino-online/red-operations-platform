"""The RED agent registry (SPEC.md section 5; queue Q3).

The registry holds one ``RedAgentSpec`` per chartered agent and refuses a
duplicate slot or routing key, so the roster is a single source of truth. ``get``
refuses an unknown key with ``UnknownRedAgentError`` rather than returning a
default, so no request reaches an agent that was never chartered.
"""

from __future__ import annotations

from collections.abc import Iterable

from redops.agents.domain.errors import (
    InvalidRedAgentSpecError,
    UnknownRedAgentError,
)
from redops.agents.domain.red_agents import RedAgentSpec, red_agent_specs


class RedAgentRegistry:
    """The immutable, validated RED agent roster."""

    def __init__(self, specs: Iterable[RedAgentSpec]) -> None:
        by_key: dict[str, RedAgentSpec] = {}
        slots: set[int] = set()
        for spec in specs:
            if not isinstance(spec, RedAgentSpec):
                raise InvalidRedAgentSpecError("the registry holds RedAgentSpec values")
            if spec.key in by_key:
                raise InvalidRedAgentSpecError(f"duplicate RED agent key {spec.key!r}")
            if spec.slot in slots:
                raise InvalidRedAgentSpecError(f"duplicate RED agent slot {spec.slot}")
            by_key[spec.key] = spec
            slots.add(spec.slot)
        self._by_key = by_key

    @classmethod
    def canonical(cls) -> "RedAgentRegistry":
        """The registry built from the section 5 roster in ``red_agents``."""
        return cls(red_agent_specs())

    def get(self, key: str) -> RedAgentSpec:
        spec = self._by_key.get(key)
        if spec is None:
            raise UnknownRedAgentError(f"unknown RED agent {key!r}")
        return spec

    def __contains__(self, key: object) -> bool:
        return key in self._by_key

    def __len__(self) -> int:
        return len(self._by_key)

    def keys(self) -> tuple[str, ...]:
        return tuple(self._by_key)

    def routable(self) -> tuple[RedAgentSpec, ...]:
        """The Director and the nine core specialists (specs with tools)."""
        return tuple(spec for spec in self._by_key.values() if spec.tools)

    def reserved(self) -> tuple[RedAgentSpec, ...]:
        """The proposal-only capability slots 10 and 11."""
        return tuple(spec for spec in self._by_key.values() if spec.is_reserved)
