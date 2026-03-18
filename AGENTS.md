# Repository Guidance

## Purpose | 文档定位

This file is the repo-level guide for AI agents and contributors working in RoboClaw.
这份文件是 RoboClaw 的仓库级指导文档，面向在本仓库内工作的 AI agent 与贡献者。

It records stable goals, boundaries, and collaboration rules. It is not an operations runbook.
它记录长期稳定的目标、边界和协作规则，不承担日常运维手册的职责。

Runtime-template instructions belong in `roboclaw/templates/AGENTS.md`, not here.
运行时模板级说明保留在 `roboclaw/templates/AGENTS.md`，不放在这里展开。

## Mission | 项目使命

RoboClaw is an open-source embodied intelligence assistant framework.
RoboClaw 是一个开源的 embodied intelligence assistant framework。

The near-term goal is to let a first-time user talk to RoboClaw, discover the setup, write setup-specific assets into workspace, and complete `connect / calibrate / move / debug / reset`.
近期目标是让第一次使用的用户能够与 RoboClaw 对话、发现现场 setup、把 setup-specific 资产写入 workspace，并完成 `connect / calibrate / move / debug / reset`。

Longer-term work should keep the path open for cross-embodiment skills, evaluation, failure analysis, recovery, and research workflows.
更长期的工作应为跨本体技能、评测、失败分析、恢复流程和研究工作流预留空间。

## Current Phase | 当前阶段优先级

The current priority is not a broad general assistant. It is the shortest reliable path from natural language to ROS2-backed execution.
当前优先级不是做一个大而全的通用助手，而是打通从自然语言到 ROS2-backed execution 的最短可靠链路。

Optimize for first-run embodied setup, reusable embodiment onboarding, and critical-path reliability before expanding feature breadth.
在扩展功能广度之前，应优先优化 first-run embodied setup、可复用的 embodiment 接入，以及关键路径的可靠性。

Prefer decisions that make the current stack easier to test, safer to operate, and easier to extend to more open-source embodiments.
优先做那些能让当前栈更易测试、更安全、更容易扩展到更多开源 embodiment 的决策。

## Hard Boundaries | 硬边界

Reusable framework behavior belongs in `roboclaw/embodied/`.
可复用的 framework 行为应放在 `roboclaw/embodied/` 中。

User-, lab-, machine-, and setup-specific assets belong in `~/.roboclaw/workspace/embodied/`, not in framework code.
用户、实验室、机器和现场 setup 相关的资产应放在 `~/.roboclaw/workspace/embodied/`，而不是 framework 代码里。

Prefer existing schema, manifests, contracts, and reusable definitions before introducing new embodiment-specific shapes.
在新增 embodiment-specific 结构之前，应优先复用已有 schema、manifest、contract 和可复用定义。

Keep the current execution assumption clear: `catalog -> runtime -> procedures -> adapters -> ROS2 -> embodiment`.
需要始终保持当前执行链路假设清晰：`catalog -> runtime -> procedures -> adapters -> ROS2 -> embodiment`。

When embodied contracts or core boundaries change, update the matching architecture or usage documents in the same change.
当 embodied contract 或核心边界发生变化时，应在同一改动中同步更新对应的架构或使用文档。

## Working Rules | 协作规则

Infer missing facts from code, docs, and local context before asking the user.
在询问用户之前，先从代码、文档和本地环境中推断缺失事实。

Do not write local device paths, namespaces, IPs, serial ids, or one-off demo assumptions into reusable framework code.
不要把本地设备路径、namespace、IP、串口标识或一次性 demo 假设写进可复用 framework 代码。

Protect the current critical path before expanding into broader features or abstractions.
在扩展更宽的功能和抽象之前，先保护当前关键路径的稳定性。

Treat `connect / calibrate / move / debug / reset` as safety-relevant flows and preserve readiness checks, stop paths, and recoverability.
把 `connect / calibrate / move / debug / reset` 视为与安全相关的流程，并保持 readiness check、stop path 和 recoverability。

Keep names, ids, and embodied contracts stable unless there is a clear migration reason.
除非有明确的迁移理由，否则应保持命名、id 和 embodied contract 稳定。

If a change affects both behavior and operator understanding, update the docs as well as the code.
如果一个改动同时影响行为和操作者理解，就应同时更新代码和文档。

## Source of Truth | 相关文档入口

Use the documents below for detailed context and implementation detail.
更详细的上下文和实现细节应以下列文档为准。

- [README.md](README.md)
- [embodiment-ros2-architecture.md](embodiment-ros2-architecture.md)
- [roboclaw-installation-guide.md](roboclaw-installation-guide.md)
- [roboclaw/embodied/README.md](roboclaw/embodied/README.md)

This file should stay shorter and more stable than those documents.
这份文件应比上述文档更短、更稳定。
