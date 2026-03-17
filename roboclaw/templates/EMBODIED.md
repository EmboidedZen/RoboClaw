# Embodied Workspace Policy

Use this workspace for setup-specific embodied assets.

`roboclaw/embodied/` is framework code. `~/.roboclaw/workspace/embodied/` is
where RoboClaw should write the active user's setup.

## Core Rule

- Edit `roboclaw/embodied/` only when changing reusable framework behavior.
- Put user-, lab-, and machine-specific assets under `embodied/` in this workspace.
- Reuse built-in robot and sensor ids when they already exist.

## First-Run Behavior

1. Start intake as soon as the user identifies the robot class or model.
2. Reuse built-in framework definitions where possible.
3. If the robot already exists in framework code, inspect its manifest and setup hints before asking follow-up questions.
4. Assume the current RoboClaw path is `catalog -> runtime -> procedures -> adapters -> ROS2 -> embodiment`.
5. Infer obvious facts from the repo, local machine, and existing workspace files before asking the user.
6. Ask only for the smallest missing fact needed for the next concrete step.
7. Generate or refine setup-specific files under `embodied/`.
8. Keep ids stable so later chat turns refine the same setup instead of creating a new one.

## User Interaction Rules

- Do not require the user to understand framework code, adapters, ROS2 namespaces, topics, actions, or file layout.
- Do not ask the user to choose between ROS2 and SDK paths during first-run setup.
- Do not front-load a large questionnaire.
- Ask one targeted question at a time.
- Defer serial devices, IPs, package paths, and driver variants until they are actually needed.
- Only ask sensor questions when they affect the generated setup or the next procedure step.

## Asset Rules

- Put local-only robot manifests in `embodied/robots/` only when framework coverage is insufficient.
- Put local-only sensor manifests in `embodied/sensors/` only when framework coverage is insufficient.
- Put topology in `embodied/assemblies/`.
- Put site-specific ROS2 and device values in `embodied/deployments/`.
- Put setup-specific adapter bindings in `embodied/adapters/`.
- Put world and scenario files in `embodied/simulators/`.
- Export `ROBOT`, `SENSOR`, `ASSEMBLY`, `DEPLOYMENT`, `ADAPTER`, `WORLD`, `SCENARIO`, or the plural form.
- Include `WORKSPACE_ASSET = WorkspaceAssetContract(...)` in generated Python files.
