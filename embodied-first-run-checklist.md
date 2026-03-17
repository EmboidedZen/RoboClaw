# RoboClaw Embodied First-Run Checklist

这份 checklist 面向第一次实际跑 RoboClaw 的人。

目标不是“完整接入所有本体”，而是验证：

- RoboClaw 能不能理解当前设备
- RoboClaw 能不能把 setup 资产写到 workspace
- RoboClaw 能不能完成 `连接 / 校准 / 移动 / debug / 复位`

## 0. 这次要验证什么

最小验收标准：

- 能启动 RoboClaw
- 能让 RoboClaw 收集 setup 信息
- 能在 workspace 下生成具身资产
- 能把资产重新加载回 catalog
- 能执行一次 connect
- 能执行一次 calibration 或跳过并说明原因
- 能执行一次小范围 move
- 能执行一次 debug
- 能执行一次 reset

## 1. 环境检查

- [ ] Python 环境已经安装好 RoboClaw
- [ ] `pip install -e ".[dev]"` 或等价安装已完成
- [ ] 你知道当前 workspace 路径
- [ ] 本体或仿真已经准备好
- [ ] ROS2 已正确安装并可用
- [ ] 能确认本体走 real 还是 sim

## 2. 启动前准备

- [ ] 确认要测试的本体类型
  - arm / hand / humanoid / mobile base / drone
- [ ] 确认是否有传感器
  - camera / depth camera / force torque / imu / lidar / other
- [ ] 确认 ROS2 信息
  - namespace
  - topics
  - services
  - actions
- [ ] 确认 deployment 信息
  - serial device / IP / port / device id / calibration path
- [ ] 确认 safety 信息
  - home/reset 模式
  - stop 方式
  - workspace 安全边界

## 3. workspace 资产生成检查

- [ ] RoboClaw 会先读取 `EMBODIED.md`
- [ ] RoboClaw 会先写 `embodied/intake/<slug>.md`
- [ ] 如果 framework 已有通用 robot / sensor，RoboClaw 会复用而不是复制
- [ ] setup-specific 文件会写到 `~/.roboclaw/workspace/embodied/`
- [ ] 不会去改 `roboclaw/embodied/` 里的 framework 源码

应该重点检查 workspace 下这些目录：

- [ ] `embodied/intake/`
- [ ] `embodied/robots/`
- [ ] `embodied/sensors/`
- [ ] `embodied/assemblies/`
- [ ] `embodied/deployments/`
- [ ] `embodied/adapters/`
- [ ] `embodied/simulators/`

## 4. catalog 回读检查

- [ ] `build_catalog(workspace)` 能加载 framework definitions
- [ ] `build_catalog(workspace)` 能加载 workspace assets
- [ ] 没有 duplicate id 报错
- [ ] 没有 schema version / migration policy 报错
- [ ] 没有缺失 export convention 报错

## 5. connect 测试

- [ ] RoboClaw 能识别当前 assembly / deployment / target
- [ ] RoboClaw 能执行 connect procedure
- [ ] adapter 能返回明确的 connect 结果
- [ ] ready / health 结果可读
- [ ] 如果失败，能说明是 dependency / transport / compatibility / safety 哪一类问题

至少记录：

- [ ] 目标 target 是什么
- [ ] 当前 adapter 是什么
- [ ] dependency check 结果
- [ ] ready / health 结果

## 6. calibrate 测试

- [ ] RoboClaw 能判断当前本体是否支持 calibration
- [ ] 如果支持，能列出 calibration targets
- [ ] 能启动 calibration
- [ ] 能跟踪 calibration 状态
- [ ] 能取消 calibration 或说明为什么不能取消

如果当前 setup 不支持 calibration，也应该验：

- [ ] RoboClaw 能明确解释原因
- [ ] 不会误导用户进入一个不存在的流程

## 7. move 测试

- [ ] RoboClaw 能执行一次最小安全动作
- [ ] 动作对应的 primitive 是清楚的
- [ ] adapter 能返回明确的 primitive execution result
- [ ] 如果动作失败，debug 信息可读

建议第一次只测小动作：

- [ ] 机械臂小幅 joint move 或 cartesian delta
- [ ] 底盘短距离移动
- [ ] 无人机最小安全模式动作

## 8. debug 测试

- [ ] RoboClaw 能执行 debug procedure
- [ ] 能读取 environment probe
- [ ] 能读取 state
- [ ] 如果有传感器，能做一次 sensor capture
- [ ] 能给出 debug snapshot / summary

要重点看：

- [ ] 结果是不是结构化
- [ ] 用户能不能看懂
- [ ] 失败时是不是能快速定位到 setup、ROS2、adapter、target 哪一层

## 9. reset 测试

- [ ] RoboClaw 能执行 reset procedure
- [ ] reset 前会先 stop/recover
- [ ] reset 完成后能回到已知安全状态
- [ ] 如果 reset 失败，能说明失败位置

## 10. 文档与引导检查

- [ ] RoboClaw 的对话引导符合 `EMBODIED.md`
- [ ] RoboClaw 的资产生成符合 `templates/embodied/README.md`
- [ ] RoboClaw 的 authoring 行为符合 `skills/embodiment-authoring/SKILL.md`
- [ ] 用户第一次使用时不会被要求直接改 framework 源码

## 11. 失败记录模板

每次卡住都建议记录：

- [ ] 卡在第几步
- [ ] 当前本体类型
- [ ] real 还是 sim
- [ ] 缺了什么信息
- [ ] 是文档问题、引导问题、workspace 资产问题、ROS2 问题，还是 adapter 问题
- [ ] 下一步应该补哪个 contract 或哪段引导

## 12. 这次试跑结束后要回答的 5 个问题

- [ ] RoboClaw 有没有把“第一次接入”引导顺
- [ ] workspace-first 这条链路有没有真的 work
- [ ] connect / calibrate / move / debug / reset 哪一步最脆弱
- [ ] 当前最大的卡点是在 agent、catalog、procedure、adapter 还是 ROS2
- [ ] 下一轮代码最该补的是哪个真实缺口
