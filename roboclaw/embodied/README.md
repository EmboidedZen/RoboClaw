# Embodied Subdomain

All robot-facing architecture lives under `roboclaw/embodied/`.

This namespace exists to prevent `roboclaw/` from becoming a flat mix of
robot definitions, transport contracts, runtime state, and deployment details.
If a module is about robots, sensors, execution targets, calibration, motion,
or simulation, it should start here instead of creating another top-level
package under `roboclaw/`.

## Layout

```text
embodied/
  ├── definition/
  │   ├── foundation/
  │   │   └── schema/
  │   ├── components/
  │   │   ├── robots/
  │   │   └── sensors/
  │   └── systems/
  │       ├── assemblies/
  │       ├── deployments/
  │       └── simulators/
  └── execution/
      ├── integration/
      │   ├── carriers/
      │   ├── transports/
      │   └── adapters/
      ├── orchestration/
      │   ├── runtime/
      │   └── procedures/
      └── observability/
          └── telemetry/
```

- `definition/`: static descriptions of embodied things
- `definition/foundation/schema/`: shared enums and structural types
- `definition/components/robots/`: robot manifests grouped by robot family, such as `arms/`
- `definition/components/sensors/`: reusable sensor manifests that can be mounted onto different robots; camera type stays generic here, while placement such as `wrist` or `overhead` belongs to assembly attachments
- `definition/systems/assemblies/`: static composition contracts and blueprint utilities; concrete user assemblies belong in workspace files
- `definition/systems/deployments/`: deployment profile contracts; concrete lab/demo/user profiles belong in workspace files
- `definition/systems/simulators/`: simulator world/scenario contracts; concrete scenarios belong in workspace files
- `execution/integration/carriers/`: execution target descriptions for real and simulated backends
- `execution/integration/transports/`: transport contracts, currently centered on ROS2
- `execution/integration/adapters/`: bindings from normalized contracts to ROS2 nodes and domain-specific execution paths
- `execution/orchestration/runtime/`: live sessions, status, active tasks, and target selection
- `execution/orchestration/procedures/`: reusable connect/calibrate/move/debug/reset flows
- `execution/observability/telemetry/`: normalized events, state snapshots, traces, and diagnostics

## Runtime Flow

The current embodied flow is:

```text
user dialogue
  -> agent guidance
  -> workspace embodied assets
  -> build_catalog(workspace)
  -> runtime session
  -> procedure
  -> adapter
  -> ROS2
  -> real or sim embodiment
```

This package only owns the framework side of that chain.
Anything specific to one lab, one robot instance, one namespace, or one camera
device belongs in workspace assets instead.

## Boundary

- `definition/` describes what the embodied system is
- `execution/integration/` describes how requests reach carriers and transports
- `execution/orchestration/` describes how one active system is selected and driven
- `execution/observability/` describes what happened while it was running
- Concrete setup files such as one user's assembly, deployment, adapter binding, or simulator scenario should be generated under `~/.roboclaw/workspace/embodied/`, not added to this package.
- `roboclaw.embodied.build_catalog(workspace)` is the merge point: it starts from built-in framework definitions and then loads workspace-generated assets back into the runtime catalog.

## First Priority

The current framework is optimized for one concrete product goal first:

- help a first-time user complete `connect / calibrate / move / debug / reset`

Other goals such as cross-embodiment skills, research replay, and richer
analysis are intentionally left as extension directions rather than fully
implemented systems.

## Rule Of Thumb

If a new feature needs to answer one of these questions, it belongs in the
matching layer:

- "What capabilities does this robot expose?" -> `definition/components/robots/`
- "What camera or tactile module is attached?" -> `definition/components/sensors/`
- "How is this robot assembled for one setup?" -> `definition/systems/assemblies/`
- "Where should one user's concrete setup files go?" -> `~/.roboclaw/workspace/embodied/`
- "Which real/sim target is active in this session?" -> `execution/orchestration/runtime/`
- "How do I call ROS2 or vendor control nodes?" -> `execution/integration/adapters/`
- "How do I connect, calibrate, debug, or reset?" -> `execution/orchestration/procedures/`
- "What changes between lab A and lab B?" -> `definition/systems/deployments/`
- "What happened during execution?" -> `execution/observability/telemetry/`
- "How do I reset or configure a virtual world?" -> `definition/systems/simulators/`
