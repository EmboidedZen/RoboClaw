# RoboClaw Agent 开发指南

## 愿景

RoboClaw 是一个 Agent 驱动的具身智能框架。用户通过自然语言完成一切——从仿真体验到真机科研。

**架构（自底向上）：**

```
本体层  真机 / 仿真器，通过 adapter 统一暴露
控制层  primitive → skill → policy，三者统一为 agent tool
科研层  数据采集 → 训练 → 推理 → 执行监督，内置 pipeline
Agent层 唯一交互面，对话驱动一切
```

**功能路线：**

| # | 功能 | 阶段 | 状态 |
|---|------|------|------|
| 1 | 对话式 onboarding（识别本体→探测→校准→就绪） | V1 | ✅ |
| 2 | Primitive 执行（connect / calibrate / run_primitive / reset） | V1 | ✅ |
| 3 | 多本体注册机制（builtins 声明 + 统一注册） | V1 | ✅ |
| 4 | 仿真环境一键启动（没有真机也能对话体验） | V1 | ✅ |
| 5 | Skill 组合（primitive 组合为 pick & place 等复合动作） | V1 | ✅ |
| 6 | 实时状态反馈（执行时 Agent 能判断是否成功） | V1 | ✅ |
| 7 | 数据采集（对话触发自动录制 episode） | V2 | ✅ |
| 8 | 训练编排（对话启动训练、汇报进展） | V2 | ✅ |
| 9 | 推理部署（对话加载模型、绑定本体） | V2 | ✅ |
| 10 | 执行监督（自动判断 episode 成败、复位、继续） | V2 | ✅ |

**当前阶段：** V1——任何本体用户连接即可通过自然语言控制。

## 写代码

- 代码交给 Codex 写（`/codex-dispatch`）。Claude Code 负责读代码、设计方案、写 worker prompt、review 结果、跑验证、与用户沟通。
- 每次结构性改动后，跑 `bash scripts/embodied_lines.sh` 并与上次对比。如果行数增长，必须给出理由或重构到不涨。向用户汇报 before/after。

## 代码规范

- 框架代码放 `roboclaw/embodied/`，用户资产放 `~/.roboclaw/workspace/embodied/`。
- 不在通用层硬编码具体本体。本体特定逻辑只能在 `builtins/<id>.py`、manifest、profile、bridge 里。
- 生产框架代码保持英文。
- 最小化代码量。不引入新抽象，除非它消除的代码比引入的更多。
- RoboClaw 对用户的对话必须保持高层次和通用化。不暴露串口路径、底层协议细节、内部技术实现。用户应无感地完成操作。

## 验证

- 本地：`python -m pytest tests/ -x -q`
- 远程 Docker：按 memory 中存储的流程执行（`reference_remote_validation.md`）
- **每个大版本功能完成后，必须在远程真机上以小白用户身份与 RoboClaw 对话，验证完整流程能否走通。测试通过不算验收，对话走通才算。**

## Review 检查项

- 重复逻辑
- 框架/setup 边界泄漏
- 通用层中的本体硬编码
- 架构偏移
- 用户对话中是否暴露了底层细节
