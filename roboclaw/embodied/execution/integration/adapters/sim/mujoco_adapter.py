"""Minimal direct Mujoco adapter for conversational embodied demos."""

from __future__ import annotations

from typing import Any

from roboclaw.embodied.definition.foundation.schema import TransportKind
from roboclaw.embodied.execution.integration.adapters.model import (
    AdapterHealthMode,
    AdapterOperation,
    AdapterOperationResult,
    AdapterStateSnapshot,
    CompatibilityCheckItem,
    CompatibilityCheckResult,
    CompatibilityComponent,
    DebugSnapshotResult,
    DependencyCheckItem,
    DependencyCheckResult,
    DependencyKind,
    EnvironmentProbeResult,
    HealthReport,
    PrimitiveExecutionResult,
    ReadinessReport,
    SensorCaptureResult,
)


class MujocoSimAdapter:
    adapter_id = "mujoco_sim"

    def __init__(self, assembly_id: str, model_path: str, joint_mapping: dict[str, str] | None = None) -> None:
        self.assembly_id = assembly_id
        self.model_path = model_path
        self.joint_mapping = joint_mapping or {}
        self._target_id: str | None = None
        self._connected = False
        self._model: Any | None = None
        self._data: Any | None = None

    def _import_mujoco(self) -> Any:
        import importlib

        return importlib.import_module("mujoco")

    def _step(self) -> None:
        self._import_mujoco().mj_step(self._model, self._data)

    def _zero_ctrl(self) -> None:
        if self._data is None:
            return
        for idx in range(len(self._data.ctrl)):
            self._data.ctrl[idx] = 0.0
        self._step()

    def probe_env(self) -> EnvironmentProbeResult:
        ok = True
        try:
            self._import_mujoco()
        except ModuleNotFoundError:
            ok = False
        return EnvironmentProbeResult(
            adapter_id=self.adapter_id,
            assembly_id=self.assembly_id,
            transport=TransportKind.DIRECT,
            available_targets=("sim",),
            detected_dependencies=("python:mujoco",) if ok else (),
            details={"ok": ok, "model_path": self.model_path},
        )

    def check_dependencies(self) -> DependencyCheckResult:
        ok, message = True, None
        try:
            self._import_mujoco()
        except ModuleNotFoundError:
            ok, message = False, "Python package 'mujoco' is not installed."
        item = DependencyCheckItem(
            dependency_id="python:mujoco",
            kind=DependencyKind.OTHER,
            required=True,
            available=ok,
            message=message,
        )
        return DependencyCheckResult(
            adapter_id=self.adapter_id,
            ok=ok,
            items=(item,),
            checked_dependencies=(item.dependency_id,),
            missing_required=() if ok else (item.dependency_id,),
        )

    async def connect(
        self,
        *,
        target_id: str,
        config: dict[str, Any] | None = None,
    ) -> AdapterOperationResult:
        path = (config or {}).get("model_path", self.model_path)
        try:
            mujoco = self._import_mujoco()
            self._model = mujoco.MjModel.from_xml_path(path)
            self._data = mujoco.MjData(self._model)
            self._target_id = target_id
            self._connected = True
            return AdapterOperationResult(AdapterOperation.CONNECT, True, target_id=target_id, details={"model_path": path})
        except ModuleNotFoundError:
            return AdapterOperationResult(
                AdapterOperation.CONNECT, False, target_id=target_id, error_code="DEP_MISSING", message="Python package 'mujoco' is not installed."
            )
        except Exception as exc:
            self._connected, self._model, self._data = False, None, None
            return AdapterOperationResult(
                AdapterOperation.CONNECT, False, target_id=target_id, error_code="CONNECT_FAILED", message=str(exc)
            )

    async def disconnect(self) -> AdapterOperationResult:
        self._connected, self._model, self._data, self._target_id = False, None, None, None
        return AdapterOperationResult(AdapterOperation.DISCONNECT, True)

    async def ready(self) -> ReadinessReport:
        return ReadinessReport(ready=self._connected, target_id=self._target_id, message=None if self._connected else "Adapter is not connected.")

    async def health(self) -> HealthReport:
        return HealthReport(
            mode=AdapterHealthMode.READY if self._connected else AdapterHealthMode.UNAVAILABLE,
            healthy=self._connected,
            error_codes=() if self._connected else ("TRANSPORT_UNAVAILABLE",),
            message=None if self._connected else "Adapter is not connected.",
        )

    async def check_compatibility(self) -> CompatibilityCheckResult:
        check = CompatibilityCheckItem(
            component=CompatibilityComponent.TRANSPORT,
            target=TransportKind.DIRECT.value,
            requirement="==direct",
            satisfied=True,
            detected_version=TransportKind.DIRECT.value,
        )
        return CompatibilityCheckResult(adapter_api_version="1.0", compatible=True, checks=(check,))

    async def stop(self, *, scope: str = "all") -> AdapterOperationResult:
        self._zero_ctrl()
        return AdapterOperationResult(AdapterOperation.STOP, True, details={"scope": scope})

    async def reset(self, *, mode: str = "home") -> AdapterOperationResult:
        self._zero_ctrl()
        return AdapterOperationResult(AdapterOperation.RESET, True, details={"mode": mode})

    async def recover(self, *, strategy: str | None = None) -> AdapterOperationResult:
        self._zero_ctrl()
        return AdapterOperationResult(AdapterOperation.RECOVER, True, details={"strategy": strategy or "default"})

    async def get_state(self) -> AdapterStateSnapshot:
        if not self._connected or self._model is None or self._data is None:
            return AdapterStateSnapshot(source="mujoco", target_id=self._target_id)
        mujoco = self._import_mujoco()
        values = {
            (mujoco.mj_id2name(self._model, mujoco.mjtObj.mjOBJ_JOINT, idx) or f"joint_{idx}"): float(self._data.qpos[self._model.jnt_qposadr[idx]])
            for idx in range(int(self._model.njnt))
        }
        if self.joint_mapping:
            values = {joint: values.get(joint, float(self._data.qpos[idx])) for idx, joint in enumerate(self.joint_mapping) if idx < len(self._data.qpos)}
        return AdapterStateSnapshot(source="mujoco", target_id=self._target_id, values=values)

    async def execute_primitive(self, name: str, args: dict[str, Any] | None = None) -> PrimitiveExecutionResult:
        if not self._connected or self._data is None or self._model is None:
            return PrimitiveExecutionResult(name, False, completed=False, status="failed", error_code="TRANSPORT_UNAVAILABLE", message="Adapter is not connected.")
        args = args or {}
        if name == "go_named_pose" and args.get("name") == "home":
            self._zero_ctrl()
            return PrimitiveExecutionResult(name, True, completed=True, status="succeeded", output={})
        commands = next((args[key] for key in ("targets", "positions", "joints") if isinstance(args.get(key), dict)), None)
        commands = commands or {key: value for key, value in args.items() if isinstance(value, (int, float))}
        try:
            mujoco = self._import_mujoco()
            for joint, value in commands.items():
                actuator = self.joint_mapping.get(joint, joint)
                actuator_id = int(mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_ACTUATOR, actuator))
                if actuator_id < 0:
                    raise KeyError(actuator)
                self._data.ctrl[actuator_id] = float(value)
            self._step()
            return PrimitiveExecutionResult(name, True, completed=True, status="succeeded", output={})
        except Exception as exc:
            return PrimitiveExecutionResult(name, False, completed=False, status="failed", error_code="COMMAND_FAILED", message=str(exc))

    async def capture_sensor(self, sensor_id: str, mode: str = "latest") -> SensorCaptureResult:
        return SensorCaptureResult(sensor_id=sensor_id, mode=mode, captured=False, message="No simulated sensors configured.")

    async def debug_snapshot(self) -> DebugSnapshotResult:
        return DebugSnapshotResult(captured=True, summary="Mujoco sim adapter snapshot", payload={"connected": self._connected, "model_path": self.model_path})
