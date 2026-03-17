"""Adapter registration types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from roboclaw.embodied.definition.foundation.schema import TransportKind

try:
    from enum import StrEnum
except ImportError:  # pragma: no cover - Python < 3.11 fallback for local tooling.
    class StrEnum(str, Enum):
        """Fallback for Python versions without enum.StrEnum."""


class AdapterOperation(StrEnum):
    """Lifecycle operation names exposed by all adapters."""

    DEPENDENCY_CHECK = "dependency_check"
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    READY = "ready"
    STOP = "stop"
    RESET = "reset"
    RECOVER = "recover"


class DependencyKind(StrEnum):
    """Dependency kinds checked before adapter activation."""

    BINARY = "binary"
    ENV_VAR = "env_var"
    DEVICE = "device"
    NETWORK = "network"
    ROS2_NODE = "ros2_node"
    ROS2_TOPIC = "ros2_topic"
    ROS2_SERVICE = "ros2_service"
    ROS2_ACTION = "ros2_action"
    OTHER = "other"


class ErrorCategory(StrEnum):
    """Normalized adapter error taxonomy."""

    DEPENDENCY = "dependency"
    TIMEOUT = "timeout"
    TRANSPORT = "transport"
    COMMAND = "command"
    SAFETY = "safety"
    INTERNAL = "internal"
    OTHER = "other"


@dataclass(frozen=True)
class DependencySpec:
    """One dependency required by an adapter binding."""

    id: str
    kind: DependencyKind
    description: str
    required: bool = True
    checker: str | None = None
    hint: str | None = None


@dataclass(frozen=True)
class OperationTimeout:
    """Timeout and retry policy for one lifecycle operation."""

    operation: AdapterOperation
    timeout_s: float
    retries: int = 0
    backoff_s: float = 0.0

    def __post_init__(self) -> None:
        if self.timeout_s <= 0:
            raise ValueError(f"Operation timeout for '{self.operation}' must be > 0.")
        if self.retries < 0:
            raise ValueError(f"Retry count for '{self.operation}' cannot be negative.")
        if self.backoff_s < 0:
            raise ValueError(f"Backoff for '{self.operation}' cannot be negative.")


@dataclass(frozen=True)
class TimeoutPolicy:
    """Default and per-operation timeout behavior."""

    default_timeout_s: float = 30.0
    operations: tuple[OperationTimeout, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.default_timeout_s <= 0:
            raise ValueError("Default timeout must be > 0.")
        operation_names = [spec.operation for spec in self.operations]
        if len(set(operation_names)) != len(operation_names):
            raise ValueError("Duplicate timeout overrides are not allowed.")

    def timeout_for(self, operation: AdapterOperation) -> OperationTimeout:
        for item in self.operations:
            if item.operation == operation:
                return item
        return OperationTimeout(operation=operation, timeout_s=self.default_timeout_s)


@dataclass(frozen=True)
class ErrorCodeSpec:
    """One machine-readable error code in adapter taxonomy."""

    code: str
    category: ErrorCategory
    description: str
    recoverable: bool = True
    retryable: bool = False
    related_operation: AdapterOperation | None = None


_REQUIRED_ADAPTER_OPERATIONS = (
    AdapterOperation.DEPENDENCY_CHECK,
    AdapterOperation.CONNECT,
    AdapterOperation.DISCONNECT,
    AdapterOperation.READY,
    AdapterOperation.STOP,
    AdapterOperation.RESET,
    AdapterOperation.RECOVER,
)


_DEFAULT_ADAPTER_ERROR_CODES = (
    ErrorCodeSpec(
        code="DEP_MISSING",
        category=ErrorCategory.DEPENDENCY,
        description="Required dependency is missing or unavailable.",
        recoverable=False,
        related_operation=AdapterOperation.DEPENDENCY_CHECK,
    ),
    ErrorCodeSpec(
        code="CONNECT_TIMEOUT",
        category=ErrorCategory.TIMEOUT,
        description="Connection timed out before adapter became ready.",
        recoverable=True,
        retryable=True,
        related_operation=AdapterOperation.CONNECT,
    ),
    ErrorCodeSpec(
        code="TRANSPORT_UNAVAILABLE",
        category=ErrorCategory.TRANSPORT,
        description="Underlying transport is unavailable.",
        recoverable=True,
        retryable=True,
    ),
    ErrorCodeSpec(
        code="RESET_FAILED",
        category=ErrorCategory.COMMAND,
        description="Reset command failed.",
        recoverable=True,
        retryable=False,
        related_operation=AdapterOperation.RESET,
    ),
    ErrorCodeSpec(
        code="RECOVER_FAILED",
        category=ErrorCategory.INTERNAL,
        description="Recovery strategy failed to restore readiness.",
        recoverable=False,
        retryable=False,
        related_operation=AdapterOperation.RECOVER,
    ),
)


@dataclass(frozen=True)
class AdapterLifecycleContract:
    """Lifecycle behavior contract for one adapter binding."""

    operations: tuple[AdapterOperation, ...] = field(default_factory=lambda: _REQUIRED_ADAPTER_OPERATIONS)
    readiness_probe: str = "ready"
    dependencies: tuple[DependencySpec, ...] = field(default_factory=tuple)
    timeout_policy: TimeoutPolicy = field(default_factory=TimeoutPolicy)
    error_codes: tuple[ErrorCodeSpec, ...] = field(default_factory=lambda: _DEFAULT_ADAPTER_ERROR_CODES)

    def __post_init__(self) -> None:
        operation_set = set(self.operations)
        missing = set(_REQUIRED_ADAPTER_OPERATIONS) - operation_set
        if missing:
            missing_ids = ", ".join(sorted(op.value for op in missing))
            raise ValueError(f"Adapter lifecycle is missing required operations: {missing_ids}.")
        if len(operation_set) != len(self.operations):
            raise ValueError("Adapter lifecycle operations cannot contain duplicates.")

        dependency_ids = [dep.id for dep in self.dependencies]
        if len(set(dependency_ids)) != len(dependency_ids):
            raise ValueError("Adapter lifecycle dependencies cannot contain duplicate ids.")

        error_codes = [item.code for item in self.error_codes]
        if len(set(error_codes)) != len(error_codes):
            raise ValueError("Adapter lifecycle error codes cannot contain duplicates.")

    def supports(self, operation: AdapterOperation) -> bool:
        return operation in set(self.operations)


DEFAULT_ADAPTER_LIFECYCLE = AdapterLifecycleContract()


@dataclass(frozen=True)
class AdapterBinding:
    """Static binding between an assembly and an implementation entrypoint."""

    id: str
    assembly_id: str
    transport: TransportKind
    implementation: str
    supported_targets: tuple[str, ...]
    bridge_id: str | None = None
    lifecycle: AdapterLifecycleContract = field(default_factory=lambda: DEFAULT_ADAPTER_LIFECYCLE)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.supported_targets:
            raise ValueError(f"Adapter '{self.id}' must support at least one execution target.")
        if len(set(self.supported_targets)) != len(self.supported_targets):
            raise ValueError(f"Adapter '{self.id}' has duplicate supported targets.")
        if self.bridge_id is not None and not self.bridge_id.strip():
            raise ValueError(f"Adapter '{self.id}' bridge_id cannot be empty when specified.")
