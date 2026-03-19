"""Runtime execution helpers for embodied procedures."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from roboclaw.agent.tools.registry import ToolRegistry
from roboclaw.embodied.definition.components.robots.model import RobotManifest
from roboclaw.embodied.definition.systems.assemblies.model import AssemblyManifest
from roboclaw.embodied.definition.systems.deployments.model import DeploymentProfile
from roboclaw.embodied.execution.integration.adapters.loader import AdapterLoader
from roboclaw.embodied.execution.integration.carriers.model import ExecutionTarget
from roboclaw.embodied.execution.orchestration.procedures.model import ProcedureKind
from roboclaw.embodied.execution.orchestration.runtime.manager import RuntimeManager
from roboclaw.embodied.execution.orchestration.runtime.model import RuntimeSession, RuntimeStatus


@dataclass(frozen=True)
class ExecutionContext:
    """Resolved embodied execution state for one setup and runtime session."""

    setup_id: str
    assembly: AssemblyManifest
    deployment: DeploymentProfile
    target: ExecutionTarget
    robot: RobotManifest
    adapter_binding: Any
    profile: Any
    runtime: RuntimeSession


@dataclass(frozen=True)
class ProcedureExecutionResult:
    """Normalized result returned to the controller."""

    procedure: ProcedureKind
    ok: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


class ProcedureExecutor:
    """Execute a small control-surface subset of embodied procedures."""

    def __init__(self, tools: ToolRegistry, runtime_manager: RuntimeManager):
        self._loader = AdapterLoader(tools)
        self._runtime_manager = runtime_manager
        self._adapters: dict[str, Any] = {}

    def runtime_for(
        self,
        *,
        runtime_id: str,
        setup_id: str,
        assembly_id: str,
        deployment_id: str,
        target_id: str,
        adapter_id: str,
    ) -> RuntimeSession:
        try:
            return self._runtime_manager.get(runtime_id)
        except KeyError:
            return self._runtime_manager.create(
                session_id=runtime_id,
                assembly_id=assembly_id,
                deployment_id=deployment_id,
                target_id=target_id,
                adapter_id=adapter_id,
            )

    def _adapter(self, context: ExecutionContext) -> Any:
        adapter = self._adapters.get(context.runtime.id)
        if adapter is None:
            adapter = self._loader.load(
                binding=context.adapter_binding,
                assembly=context.assembly,
                deployment=context.deployment,
                target=context.target,
                robot=context.robot,
                profile=context.profile,
            )
            self._adapters[context.runtime.id] = adapter
        return adapter

    async def execute_connect(
        self,
        context: ExecutionContext,
        *,
        on_progress: Any | None = None,
    ) -> ProcedureExecutionResult:
        preflight = self._ensure_calibration_ready(context)
        if preflight is not None and context.runtime.status != RuntimeStatus.READY:
            return preflight

        adapter = self._adapter(context)
        context.runtime.status = RuntimeStatus.CONNECTING

        probe = adapter.probe_env()
        deps = adapter.check_dependencies()
        if not deps.ok:
            missing = ", ".join(deps.missing_required) or "required ROS2 interfaces"
            context.runtime.status = RuntimeStatus.ERROR
            context.runtime.last_error = missing
            return ProcedureExecutionResult(
                procedure=ProcedureKind.CONNECT,
                ok=False,
                message=f"Setup `{context.setup_id}` is not ready yet: missing {missing}.",
                details={"probe": probe.details, "missing_required": deps.missing_required},
            )

        connected = await adapter.connect(
            target_id=context.target.id,
            config=dict(context.deployment.connection),
        )
        if not connected.ok:
            context.runtime.status = RuntimeStatus.ERROR
            context.runtime.last_error = connected.message or connected.error_code
            return ProcedureExecutionResult(
                procedure=ProcedureKind.CONNECT,
                ok=False,
                message=connected.message or f"Failed to connect setup `{context.setup_id}`.",
                details={"error_code": connected.error_code, **connected.details},
            )

        ready = await adapter.ready()
        if not ready.ready:
            context.runtime.status = RuntimeStatus.ERROR
            context.runtime.last_error = ready.message
            return ProcedureExecutionResult(
                procedure=ProcedureKind.CONNECT,
                ok=False,
                message=ready.message or f"Setup `{context.setup_id}` is not ready for commands yet.",
                details={"blocked_operations": [item.value for item in ready.blocked_operations], **ready.details},
            )

        context.runtime.status = RuntimeStatus.READY
        context.runtime.last_error = None
        return ProcedureExecutionResult(
            procedure=ProcedureKind.CONNECT,
            ok=True,
            message=f"Connected setup `{context.setup_id}` on target `{context.target.id}`.",
            details={"probe": probe.details, "target_id": context.target.id},
        )

    async def execute_move(
        self,
        context: ExecutionContext,
        *,
        primitive_name: str,
        primitive_args: dict[str, Any] | None = None,
        on_progress: Any | None = None,
    ) -> ProcedureExecutionResult:
        if context.runtime.status != RuntimeStatus.READY:
            connected = await self.execute_connect(context, on_progress=on_progress)
            if not connected.ok:
                return connected

        adapter = self._adapter(context)
        context.runtime.status = RuntimeStatus.BUSY
        pre_state = await adapter.get_state()
        primitive = await adapter.execute_primitive(primitive_name, primitive_args or {})
        if not primitive.accepted:
            context.runtime.status = RuntimeStatus.ERROR
            context.runtime.last_error = primitive.message or primitive.error_code
            return ProcedureExecutionResult(
                procedure=ProcedureKind.MOVE,
                ok=False,
                message=primitive.message or f"Primitive `{primitive_name}` was rejected.",
                details={"error_code": primitive.error_code, **primitive.output},
            )

        post_state = await adapter.get_state()
        context.runtime.status = RuntimeStatus.READY
        context.runtime.last_error = None
        completion = "completed" if primitive.completed is not False else "accepted"
        state_message = self._state_confirmation(primitive_name, pre_state.values, post_state.values)
        message = f"Primitive `{primitive_name}` {completion} on setup `{context.setup_id}`."
        if state_message:
            message = f"{message} {state_message}"
        return ProcedureExecutionResult(
            procedure=ProcedureKind.MOVE,
            ok=True,
            message=message,
            details={
                "state_before": pre_state.values,
                "state_after": post_state.values,
                **primitive.output,
            },
        )

    async def execute_debug(self, context: ExecutionContext) -> ProcedureExecutionResult:
        adapter = self._adapter(context)
        probe = adapter.probe_env()
        state = await adapter.get_state()
        snapshot = await adapter.debug_snapshot()
        context.runtime.status = RuntimeStatus.READY if snapshot.captured else RuntimeStatus.ERROR
        if not snapshot.captured:
            context.runtime.last_error = snapshot.message or snapshot.summary
        return ProcedureExecutionResult(
            procedure=ProcedureKind.DEBUG,
            ok=snapshot.captured,
            message=snapshot.summary,
            details={"probe": probe.details, "state": state.values, "artifacts": snapshot.artifacts},
        )

    async def execute_reset(self, context: ExecutionContext) -> ProcedureExecutionResult:
        adapter = self._adapter(context)
        stop_result = await adapter.stop(scope="all")
        reset_result = await adapter.reset(mode="home")
        if not reset_result.ok:
            context.runtime.status = RuntimeStatus.ERROR
            context.runtime.last_error = reset_result.message or reset_result.error_code
            return ProcedureExecutionResult(
                procedure=ProcedureKind.RESET,
                ok=False,
                message=reset_result.message or f"Failed to reset setup `{context.setup_id}`.",
                details={
                    "stop_message": stop_result.message,
                    "error_code": reset_result.error_code,
                    **reset_result.details,
                },
            )

        context.runtime.status = RuntimeStatus.READY
        context.runtime.last_error = None
        return ProcedureExecutionResult(
            procedure=ProcedureKind.RESET,
            ok=True,
            message=reset_result.message or f"Reset setup `{context.setup_id}` to home.",
            details={"stop_message": stop_result.message, **reset_result.details},
        )

    async def execute_calibrate(
        self,
        context: ExecutionContext,
        *,
        on_progress: Any | None = None,
    ) -> ProcedureExecutionResult:
        calibration_path = self._calibration_path(context)
        if calibration_path is not None and calibration_path.exists():
            return ProcedureExecutionResult(
                procedure=ProcedureKind.CALIBRATE,
                ok=True,
                message=(
                    f"Setup `{context.setup_id}` already has a calibration file at `{calibration_path}`. "
                    "You can retry `connect` or your motion command."
                ),
                details={"calibration_path": str(calibration_path)},
            )

        if getattr(context.profile, "robot_id", None) == "so101":
            return await self._execute_so101_calibration_guide(context, on_progress=on_progress)

        expected_path = str(calibration_path) if calibration_path is not None else None
        return ProcedureExecutionResult(
            procedure=ProcedureKind.CALIBRATE,
            ok=False,
            message=(
                f"Setup `{context.setup_id}` needs calibration before execution."
                + (f" Expected canonical path: `{expected_path}`." if expected_path else "")
                + " Reply with `calibrate` after the hardware is ready so RoboClaw can walk you through it."
            ),
        )

    def _calibration_path(self, context: ExecutionContext) -> Path | None:
        profile = context.profile
        if profile is None or not getattr(profile, "requires_calibration", False):
            return None
        return profile.canonical_calibration_path()

    def _ensure_calibration_ready(self, context: ExecutionContext) -> ProcedureExecutionResult | None:
        calibration_path = self._calibration_path(context)
        if calibration_path is None or calibration_path.exists():
            return None

        context.runtime.status = RuntimeStatus.ERROR
        context.runtime.last_error = f"Missing calibration file: {calibration_path}"
        return ProcedureExecutionResult(
            procedure=ProcedureKind.CALIBRATE,
            ok=False,
            message=(
                f"Setup `{context.setup_id}` needs calibration before `connect` or motion."
                f" Expected canonical path: `{calibration_path}`."
                " Reply with `calibrate` to start the live SO101 calibration guide."
            ),
            details={"calibration_path": str(calibration_path)},
        )

    @staticmethod
    def _serial_device_by_id(context: ExecutionContext) -> str | None:
        device = str(context.deployment.connection.get("serial_device_by_id") or "").strip()
        if device:
            return device
        for robot_config in context.deployment.robots.values():
            candidate = str(robot_config.get("serial_device_by_id") or "").strip()
            if candidate:
                return candidate
        return None

    def _build_so101_calibration_monitor(self, context: ExecutionContext) -> Any:
        from roboclaw.embodied.execution.integration.control_surfaces.ros2.so101_feetech import So101CalibrationMonitor

        device_by_id = self._serial_device_by_id(context)
        if not device_by_id:
            raise RuntimeError("No stable `/dev/serial/by-id/...` device is configured for this setup yet.")
        return So101CalibrationMonitor(device_by_id=device_by_id)

    async def _execute_so101_calibration_guide(
        self,
        context: ExecutionContext,
        *,
        on_progress: Any | None = None,
    ) -> ProcedureExecutionResult:
        calibration_path = self._calibration_path(context)
        try:
            monitor = self._build_so101_calibration_monitor(context)
            monitor.connect()
            monitor.prepare_manual_calibration()
            interval_s, heartbeat_s, sample_limit = self._so101_calibration_stream_settings()
            stream_result = await self._stream_so101_calibration_view(
                monitor,
                calibration_path=calibration_path,
                on_progress=on_progress,
                interval_s=interval_s,
                heartbeat_s=heartbeat_s,
                sample_limit=sample_limit,
            )
        except Exception as exc:
            context.runtime.status = RuntimeStatus.ERROR
            context.runtime.last_error = str(exc)
            return ProcedureExecutionResult(
                procedure=ProcedureKind.CALIBRATE,
                ok=False,
                message=(
                    "RoboClaw could not start the live SO101 calibration guide."
                    f" {exc}"
                ),
            )
        finally:
            if "monitor" in locals():
                monitor.disconnect()

        context.runtime.status = RuntimeStatus.DISCONNECTED
        context.runtime.last_error = None
        expected_path = str(calibration_path) if calibration_path is not None else "unknown"
        if stream_result == "saved":
            return ProcedureExecutionResult(
                procedure=ProcedureKind.CALIBRATE,
                ok=True,
                message=(
                    f"SO101 calibration file detected at `{expected_path}`."
                    " You can retry `connect` or your motion command now."
                ),
                details={"calibration_path": expected_path},
            )

        final_clause = (
            " Move the arm by hand and keep watching the live values until you save the canonical calibration file."
        )
        if sample_limit is not None:
            final_clause = (
                " The bounded test stream finished."
                " Move the arm by hand while watching those live values, then create the canonical calibration file"
                " before retrying `connect`."
            )
        return ProcedureExecutionResult(
            procedure=ProcedureKind.CALIBRATE,
            ok=False,
            message=(
                f"Live SO101 calibration stream started for setup `{context.setup_id}`."
                " RoboClaw disabled torque and streamed a LeRobot-style `MIN | POS | MAX` table above."
                + final_clause
                + f" Expected canonical path: `{expected_path}`."
            ),
            details={"calibration_path": expected_path},
        )

    def _so101_calibration_stream_settings(self) -> tuple[float, float, int | None]:
        interval_s = 0.2
        heartbeat_s = 1.0
        raw_limit = os.environ.get("ROBOCLAW_SO101_CALIBRATION_SAMPLE_LIMIT", "").strip()
        sample_limit = int(raw_limit) if raw_limit else None
        return interval_s, heartbeat_s, sample_limit

    async def _stream_so101_calibration_view(
        self,
        monitor: Any,
        *,
        calibration_path: Path | None,
        on_progress: Any | None,
        interval_s: float,
        heartbeat_s: float,
        sample_limit: int | None,
    ) -> str:
        sample_idx = 0
        last_payload = ""
        last_emit = 0.0
        while True:
            sample_idx += 1
            snapshot = monitor.snapshot()
            payload = self._format_so101_calibration_snapshot(snapshot, sample_idx=sample_idx)
            now = asyncio.get_running_loop().time()
            if on_progress is not None and (payload != last_payload or (now - last_emit) >= heartbeat_s):
                await on_progress(payload)
                last_emit = now
                last_payload = payload
            if calibration_path is not None and calibration_path.exists():
                return "saved"
            if sample_limit is not None and sample_idx >= sample_limit:
                return "sample_limit"
            await asyncio.sleep(interval_s)

    @staticmethod
    def _format_so101_calibration_snapshot(snapshot: Any, *, sample_idx: int) -> str:
        def _cell(value: int | None) -> str:
            return "?" if value is None else str(value)

        lines = [
            f"SO101 calibration live view frame {sample_idx} on `{snapshot.resolved_device or snapshot.device_by_id}`",
            "```text",
            "JOINT            ID     MIN    POS    MAX",
        ]
        for row in snapshot.rows:
            lines.append(
                f"{row.joint_name:<16} {row.servo_id:>2} { _cell(row.range_min_raw):>7} { _cell(row.position_raw):>6} { _cell(row.range_max_raw):>6}"
            )
        lines.append("```")
        return "\n".join(lines)

    @staticmethod
    def _state_confirmation(
        primitive_name: str,
        pre_state: dict[str, Any],
        post_state: dict[str, Any],
    ) -> str:
        gripper_before = ProcedureExecutor._gripper_percent(pre_state)
        gripper_after = ProcedureExecutor._gripper_percent(post_state)
        if primitive_name in {"gripper_open", "gripper_close"} and gripper_after is not None:
            if primitive_name == "gripper_open":
                label = "open" if gripper_after >= 60 else "partially open"
            elif primitive_name == "gripper_close":
                label = "closed" if gripper_after <= 40 else "partially open"
            elif gripper_after >= 80:
                label = "open"
            elif gripper_after <= 20:
                label = "closed"
            else:
                label = "partially open"
            if gripper_before is not None:
                return (
                    f"Current gripper state: {label} "
                    f"({gripper_after:.1f}% open, was {gripper_before:.1f}%)."
                )
            return f"Current gripper state: {label} ({gripper_after:.1f}% open)."
        return ""

    @staticmethod
    def _gripper_percent(values: dict[str, Any]) -> float | None:
        raw = values.get("gripper_percent")
        if raw is None:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None
