"""Small per-run tool registry used by the GAIA agent loop."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from jsonschema import validate


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]
    function: Callable[..., str]
    dangerous: bool = False
    parallel_safe: bool = False

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self.approval = None
        self.audit = lambda **event: None
        self._serial_lock = threading.RLock()

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        function: Callable[..., str],
        *,
        dangerous: bool = False,
        parallel_safe: bool = False,
    ) -> None:
        if name in self._tools:
            raise ValueError(f"tool {name!r} is already registered")
        self._tools[name] = ToolDefinition(name, description, parameters, function, dangerous, parallel_safe)

    def subset(self, names: set[str]) -> ToolRegistry:
        child = ToolRegistry()
        child._tools = {k: v for k, v in self._tools.items() if k in names}
        child.approval, child.audit = self.approval, self.audit
        child._serial_lock = self._serial_lock
        return child

    def is_parallel_safe(self, name: str) -> bool:
        tool = self._tools.get(name)
        return bool(tool and tool.parallel_safe and not tool.dangerous)

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.schema() for tool in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools)

    def execute(self, name: str, arguments_json: str) -> tuple[str, bool]:
        definition = self._tools.get(name)
        if definition is None:
            self.audit(action="unknown_tool", tool=name)
            return f"ERROR: unknown tool {name!r}; available={self.names()}", False
        try:
            arguments = json.loads(arguments_json)
            if not isinstance(arguments, dict):
                raise TypeError("arguments must be a JSON object")
            validate(arguments, definition.parameters)
            self.audit(action="validated", tool=name)
            if definition.dangerous:
                approved = bool(self.approval and self.approval(name, arguments))
                self.audit(action="approval", tool=name, approved=approved)
                if not approved:
                    return "DENIED: human approval required", False
            if definition.parallel_safe and not definition.dangerous:
                result = definition.function(**arguments)
            else:
                with self._serial_lock:
                    result = definition.function(**arguments)
            self.audit(action="executed", tool=name, success=True)
            return str(result), True
        except Exception as exc:  # noqa: BLE001 - tool failures become observations.
            self.audit(action="rejected_or_failed", tool=name, error=type(exc).__name__)
            return f"ERROR: {name} failed: {type(exc).__name__}: {exc}", False
