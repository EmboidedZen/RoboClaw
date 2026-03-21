from types import SimpleNamespace

import pytest

from roboclaw.embodied.execution.integration.adapters.sim import MujocoSimAdapter


def _fake_mujoco():
    class _Model:
        njnt = 2
        jnt_qposadr = [0, 1]

        @classmethod
        def from_xml_path(cls, path):
            inst = cls()
            inst.path = path
            return inst

    class _Data:
        def __init__(self, model):
            self.qpos = [0.1, -0.2]
            self.ctrl = [0.0, 0.0]

    names = {0: "joint_a", 1: "joint_b"}
    actuators = {"joint_a": 0, "act_b": 1}
    return SimpleNamespace(
        MjModel=_Model,
        MjData=_Data,
        mjtObj=SimpleNamespace(mjOBJ_JOINT=1, mjOBJ_ACTUATOR=2),
        mj_step=lambda model, data: None,
        mj_id2name=lambda model, obj, idx: names[idx],
        mj_name2id=lambda model, obj, name: actuators[name],
    )


def test_adapter_instantiation():
    assert MujocoSimAdapter("arm", "robot.xml").assembly_id == "arm"


def test_probe_env_without_mujoco(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("importlib.import_module", lambda name: (_ for _ in ()).throw(ModuleNotFoundError()) if name == "mujoco" else None)
    assert MujocoSimAdapter("arm", "robot.xml").probe_env().details["ok"] is False


@pytest.mark.asyncio
async def test_connect_disconnect_and_get_state(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("importlib.import_module", lambda name: _fake_mujoco())
    adapter = MujocoSimAdapter("arm", "robot.xml")
    assert (await adapter.connect(target_id="sim")).ok is True
    assert (await adapter.get_state()).values == {"joint_a": 0.1, "joint_b": -0.2}
    assert (await adapter.disconnect()).ok is True


@pytest.mark.asyncio
async def test_execute_primitive(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("importlib.import_module", lambda name: _fake_mujoco())
    adapter = MujocoSimAdapter("arm", "robot.xml", {"joint_b": "act_b"})
    await adapter.connect(target_id="sim")
    result = await adapter.execute_primitive("move_joints", {"targets": {"joint_b": 0.5}})
    assert result.accepted is True
