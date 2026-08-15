# 信号矩阵策略实施 — 新会话交接指南

**日期**: 2026-08-15
**会话状态**: 设计文档+计划完成，git 已初始化，等待新会话开始实施

---

## ✅ 本次会话已完成

| 任务 | 文件 |
|------|------|
| 设计文档（11 章节 + 30+ 漏洞修复） | `docs/superpowers/specs/2026-08-15-signal-matrix-strategy-design.md` |
| 实施计划（17 任务 TDD） | `docs/superpowers/plans/2026-08-15-signal-matrix-strategy-plan.md` |
| Git 仓库初始化 | git 已用 zealotred@gmail.com / JulyZhang 配置 |
| `.gitignore` 创建 | 仅追踪 `strategy/` 新文件，不污染现有项目 |
| 任务跟踪清单 | TaskCreate 已建立（18 个任务） |

---

## 🚀 新会话启动指令

在新会话中，**直接发送以下内容**即可继续：

```
使用 superpowers:subagent-driven-development 技能，严格执行实施计划：
docs/superpowers/plans/2026-08-15-signal-matrix-strategy-plan.md

设计文档参考：
docs/superpowers/specs/2026-08-15-signal-matrix-strategy-design.md

工作目录：C:\Users\Administrator\claude
Git 已初始化，commit 信息需清晰，遵循 TDD（先测试，后实现）
```

---

## 📋 实施顺序（17 任务）

按依赖顺序：

1. **Task 1**: 项目骨架 + Config
2. **Task 2**: ATR 工具（漏洞 I 零值保护）
3. **Task 3**: 通用指标（漏洞 E 除零保护）
4. **Task 4**: 数据加载
5. **Task 5**: 场景识别（5 步顺序过滤器）
6. **Task 6**: 缠论门控（漏洞 D/G/H/I）
7. **Task 7**: SMC（漏洞 J/K/L/M）
8. **Task 8**: 传统指标（漏洞 N/O/P/Q）
9. **Task 9**: 三层加权（漏洞 R/S/T/U）
10. **Task 10**: 期望值卡片（漏洞 V/W/X/Y）
11. **Task 11**: 分级仓位（漏洞 Z + AK）
12. **Task 12**: 适配器（漏洞 AE）
13. **Task 13**: 订单执行器（漏洞 AD/AI/AJ）
14. **Task 14**: 标的筛选 + 回测引擎
15. **Task 15**: 监控与日志
16. **Task 16**: 主入口 + 端到端
17. **Task 17**: 回测脚本（用 backtest_data/ 数据）

---

## ⚠️ 关键提醒

1. **每次 subagent dispatch 必须包含完整任务文本**（不要让 subagent 读 plan 文件）
2. **两阶段 review**：spec compliance review → code quality review
3. **每个任务 5 步**：写测试 → 运行确认失败 → 实现 → 运行确认通过 → git commit
4. **commit 信息要清晰**，便于后续追溯
5. **本会话已修复 30+ 漏洞**，实施时务必遵守 spec 中的修正逻辑，不要"简化"或"优化"

---

## 📂 关键文件路径

```
C:\Users\Administrator\claude\
├── .git/                              # git 已初始化
├── .gitignore                         # 排除现有项目
├── strategy/                          # 【即将创建】所有新代码
│   ├── __init__.py
│   ├── config.py
│   ├── data/
│   ├── indicators/
│   ├── scoring/
│   ├── signals/
│   ├── position/
│   ├── execution/
│   ├── adapters/
│   ├── backtest/
│   ├── monitor/
│   ├── universe/
│   ├── utils/
│   └── main.py
├── tests/                             # 【即将创建】所有测试
├── scripts/                           # 【即将创建】回测脚本
│   └── run_backtest.py
├── backtest_data/                     # 已有数据，不要修改
├── docs/superpowers/
│   ├── specs/2026-08-15-signal-matrix-strategy-design.md   # 设计文档
│   ├── plans/2026-08-15-signal-matrix-strategy-plan.md     # 实施计划
│   └── handoff-2026-08-15-signal-matrix.md                # 本文件
```

---

## 🎯 最终交付目标

完成后，您将拥有：
1. 完整的 `strategy/` Python 包（17 个模块）
2. `tests/` 完整测试套件
3. 可运行的 `scripts/run_backtest.py`
4. 在 `backtest_data/` 已有数据上跑通回测
5. 17 个清晰的 git commit

---

**新会话一句话启动**：
> 使用 superpowers:subagent-driven-development 执行 `docs/superpowers/plans/2026-08-15-signal-matrix-strategy-plan.md`，参考 `docs/superpowers/specs/2026-08-15-signal-matrix-strategy-design.md`

---

**祝顺利！🚀**