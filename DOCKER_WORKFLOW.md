# Docker Workflow

Use this guide after Docker installation is already working. It covers the
normal RoboClaw Docker development loop and the matrix validation flow.

## Development Model

- Dev containers are bind-mounted to the host RoboClaw repo for fast iteration.
- Validation images are immutable and built from a clean Git worktree.
- Use the dev container for coding and local checks.
- Use the matrix workflow for clean acceptance validation.

## Start or Re-enter a Dev Container

Start a long-lived dev container for one instance and profile:

```bash
./scripts/docker/start-dev.sh devbox --profile ubuntu2404-ros2
./scripts/docker/exec-dev.sh devbox --profile ubuntu2404-ros2
```

If no dev image exists yet, `start-dev.sh` builds a mutable dev image for that
profile without requiring a clean Git worktree.

The dev container mounts the host repo at `/roboclaw-source` and uses it first on `PYTHONPATH`,
so ordinary source edits are visible immediately without rebuilding the image.

The dev container still uses the same isolated instance state under:

```text
~/.roboclaw-docker/instances/<instance>--<profile>/
```

That instance directory stores:

- `config.json`
- `workspace/`
- `calibration/`
- runtime user state under `home/`

The bootstrap step seeds instance-local calibration from the host's canonical
`~/.roboclaw/calibration/` tree when it exists. If that tree is empty but a
compatible legacy calibration cache exists, the bootstrap step imports it once
into the instance-local canonical layout.

## Normal Development Loop

The expected loop is:

1. Start or re-enter the dev container.
2. Edit code on the host.
3. Run the command or test you are working on inside the dev container.
4. Repeat without rebuilding for ordinary source edits.
5. Use matrix validation before acceptance-sensitive changes are considered done.

For normal Python source edits, keep the dev container running and rerun the
command you are testing.

## When To Rebuild

Use `build-image.sh` only when the runtime environment changes:

- Dockerfile changes
- ROS/system dependency changes
- explicit Python dependency changes
- release or acceptance validation

To verify that a running dev container sees host source edits without a rebuild, use:

```bash
./tests/test_docker_dev_bind_mount.sh
```

## Dependencies

`scservo_sdk` ships as part of the RoboClaw source tree, so the Docker image no
longer depends on a host-side site-packages drop.

## Matrix Validation Workflow

Use the matrix workflow for reproducible acceptance runs across the supported
ROS2 profiles.

### Profiles

Default validation profiles:

- `ubuntu2204-ros2`
- `ubuntu2404-ros2`

Each profile is built from a clean Git worktree and tagged with the instance
name, profile, and current short commit hash.

### Build the Matrix

Build the matrix for one instance:

```bash
./scripts/docker/matrix.sh build devbox
```

The build entrypoint requires a clean Git worktree. If the worktree is dirty,
the build stops before any image is produced.

### Run a Validation Task

Run the same RoboClaw command across the matrix:

```bash
./scripts/docker/matrix.sh run-task devbox -- status
./scripts/docker/matrix.sh run-task devbox -- agent -m "hello" --no-markdown
```

For embodied validation, use a bounded command sequence such as:

```bash
./scripts/docker/matrix.sh run-task devbox -- agent -m "I want to connect a real robot. Please guide me step by step."
```

Then continue the conversation with the device and setup facts that RoboClaw
requests.

For a fixed SO101 acceptance run across both ROS2 profiles, use:

```bash
./tests/test_matrix_so101_acceptance.sh
```

That helper builds the immutable matrix, runs this five-message sequence on
each profile, requires `gripper_open` and `gripper_close` to complete through
the framework path, and then checks that the persisted session metadata
contains only `/dev/serial/by-id/...` device identifiers:

- `I want to connect a real robot`
- `SO101`
- `connected`
- `open the gripper`
- `close the gripper`

### Validation Notes

- Build uses host networking.
- Runtime uses host networking.
- Proxy values are discovered on the remote host and propagated into the build
  and runtime.
- Validation containers use immutable image tags and do not bind-mount the host
  repo.
- Instance-local calibration is prepared under
  `~/.roboclaw-docker/instances/<instance>--<profile>/calibration/`.
- Session metadata and generated deployment facts persist
  `/dev/serial/by-id/...` identifiers only.

### Cleanup

The matrix workflow is designed to keep build cache available. Avoid removing
image layers unless you intentionally want a cold rebuild.
