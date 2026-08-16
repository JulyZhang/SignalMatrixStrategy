# 信号矩阵策略（Signal Matrix Strategy）

融合缠论、SMC（Smart Money Concepts）和传统指标的 A 股可回测交易策略。信号矩阵 × 期望值卡片架构，所有信号统一转化为「期望空间 / 止损空间 / 置信度」三选一形式输出。

> 📚 完整设计文档：`docs/superpowers/specs/2026-08-15-signal-matrix-strategy-design.md`
> 📋 实施计划：`docs/superpowers/plans/2026-08-15-signal-matrix-strategy-plan.md`

---

## 1. 环境要求

- Python 3.11+（实测 3.14.5 工作）
- pandas、numpy、pytest（已通过 `pyproject.toml` 声明）
- 可选：`akshare`（实盘数据接入，本仓库暂未启用）

```bash
# 克隆后安装依赖（推荐使用虚拟环境）
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

---

## 2. 项目结构

```
strategy/                       # 核心策略包
├── config.py                   # 全局配置（参数、阈值、权重）— 改这里调参
├── main.py                     # 主入口 run_strategy_on_bar()
├── data/                       # 数据加载 + 质量检查
├── indicators/                 # 三层信号层（chanlun / smc / traditional）
├── scoring/                    # 场景识别 + 三层加权
├── signals/                    # 期望值卡片
├── position/                   # 分级仓位 + PositionLot 批次追踪
├── adapters/                   # 市场适配器（A 股 + 期货预留）
├── execution/                  # 订单执行器（T+1、涨跌停、滑点）
├── universe/                   # 标的筛选
├── backtest/                   # 回测引擎骨架
├── monitor/                    # 监控与日志
└── utils/                      # ATR / EMA / MACD / RSI 通用工具

scripts/
├── run_backtest.py             # 回测脚本（命令行入口）
└── calc_metrics.py             # 绩效指标计算

tests/                          # 72 个测试，覆盖 17 个任务
backtest_data/                  # 已有历史数据（stk_*.csv）
```

---

## 3. 快速开始：跑一次回测

```bash
# 默认跑前 5 只股票全量回测（约 5 分钟，生成 1700+ 个信号）
python scripts/run_backtest.py

# 跑全部股票（耗时随股票数线性增长，建议先用 max_bars 限制）
# 改 scripts/run_backtest.py 中的 main() 调用即可，例如：
#   main(symbols=["600519", "000333"], max_bars=500)
```

输出示例：
```
回测完成，共生成 1706 个有效信号
```

### 计算绩效指标

```bash
# 默认：跑回测 + 打印场景/置信度分布
python scripts/calc_metrics.py
```

输出示例：
```
=== 回测绩效指标 ===
总信号数: 1706
涉及股票数: 5
平均置信度: 0.6523
置信度区间: [0.5120, 0.8912]

场景分布:
  趋势市: 1245 (73.0%)
  拐点市: 312 (18.3%)
  震荡市: 149 (8.7%)

置信度档位分布:
  高: 892 (52.3%)
  中: 567 (33.2%)
  极高: 247 (14.5%)
```

---

## 4. 编程接口：单根 K 线决策

最常用的入口是 `run_strategy_on_bar()`，对单根 bar 跑完整 7 步决策流程：

```python
from strategy.main import run_strategy_on_bar
from strategy.signals.expectation_card import ExpectationCard

# 准备数据（示例）
import pandas as pd
import numpy as np

dates = pd.date_range("2022-01-01", periods=500, freq="D")
daily_close = pd.Series(np.linspace(10, 50, 500), index=dates)
daily_high = daily_close * 1.02
daily_low = daily_close * 0.98
daily_open = daily_close.shift(1).fillna(daily_close.iloc[0])
daily_volume = pd.Series([1e7] * 500, index=dates)

weekly_close = daily_close.resample("W").last().dropna()
weekly_volume = daily_volume.resample("W").sum().dropna()

current_bar = {
    "close": daily_close.iloc[-1],
    "high": daily_high.iloc[-1],
    "low": daily_low.iloc[-1],
    "成交额": 1e8,
    "date": str(dates[-1].date()),
    "prev_close": daily_close.iloc[-2],
    "停牌": False,
}

# 调用
card: ExpectationCard | None = run_strategy_on_bar(
    symbol="000001",
    daily_close=daily_close,
    daily_high=daily_high,
    daily_low=daily_low,
    daily_open=daily_open,         # Task 16 后必填
    daily_volume=daily_volume,
    weekly_close=weekly_close,
    weekly_volume=weekly_volume,
    current_bar=current_bar,
)

if card is None:
    print("无信号（被门控或加权层否决）")
else:
    print(f"置信度: {card.confidence:.4f} ({card.confidence_tier})")
    print(f"入场价: {card.entry_price}, 止损: {card.stop_loss}")
    print(f"TP1/TP2/TP3: {card.tp1}/{card.tp2}/{card.tp3}")
    print(f"入场策略: {card.entry_strategy}")
    print(f"风报比 RR: {card.risk_reward_ratio:.2f}")
    print(f"场景: {card.scene}")
```

`card` 是 `ExpectationCard` 数据类（详见 `strategy/signals/expectation_card.py`），包含入场价、止损、三个目标位、风险回报比、置信度档位、入场策略等信息。

---

## 5. 配置调参

所有阈值、权重、滑点都集中在 `strategy/config.py` 单点管理：

```python
from strategy.config import Config

Config.WEIGHT_MATRIX["趋势市"]   # 三层加权矩阵（按场景）
Config.CONFIDENCE_TIERS           # 置信度档位阈值
Config.POSITION_TIERS             # 仓位档位上限
Config.LIMIT_PCT                  # 涨跌停幅度（主板 10% / 创业板 20%）
Config.SLIPPAGE_BY_LIQUIDITY      # 滑点（按成交额三档）
Config.COMMISSION_RATE            # 佣金率 0.03%
Config.STAMP_TAX_SELL             # 印花税 0.1%
Config.MIN_AVG_TURNOVER           # 标的筛选最低成交额 5000 万
Config.MIN_PRICE                  # 标的筛选最低股价 1 元
```

调整后无需重启 — Python 进程内直接生效。

---

## 6. 测试

```bash
# 全部 72 个测试
pytest tests/ -v

# 单个文件
pytest tests/test_config.py -v

# 特定测试
pytest tests/test_e2e.py::test_e2e_full_pipeline_with_sufficient_history -v

# 带覆盖率（可选）
pip install pytest-cov
pytest tests/ --cov=strategy --cov-report=term-missing
```

---

## 7. 端到端流程图

```
数据源 (backtest_data/*.csv)
        ↓
[Task 4] 数据加载 (load_stock_csv) → DatetimeIndex + 标准列名
        ↓
[Task 5] 场景识别 (recognize_scene) → Scene_Snapshot
        ↓
[Task 6] 缠论门控 (calc_chanlun_gate) → C_缠论 / 否决
        ↓
[Task 7] SMC 行为层 (calc_c_smc) → C_SMC / 期望空间边界
        ↓
[Task 8] 传统指标层 (calc_c_traditional) → C_传统
        ↓
[Task 9] 三层加权 (calc_weighted_score) → C_总 / 置信度档位
        ↓
[Task 10] 期望值卡片 (build_expectation_card) → ExpectationCard
        ↓
[Task 11] 分级仓位 (calc_position_size) → position_size
        ↓
[Task 13] 订单执行器 (OrderExecutor.execute_first_batch) → List[Order]
        ↓
[Task 15] 监控日志 (log_signal / log_trade)
```

每个环节都可能返回 `None` 或「否决」状态，决策终止。

---

## 8. 关键设计原则

1. **缠论是骨架**：永远先做门控，不通过则不交易
2. **所有输出必须可转化为三选一**：期望空间 / 止损空间 / 置信度
3. **不能转化的信息 = 噪音**，不参与决策
4. **「宁可错过，不做错」**：模糊地带默认归入「中阴态」并拒绝开仓

---

## 9. 已知限制

- **期货适配器是占位实现**：`FuturesAdapter.calc_trading_cost` 返回 0，仅供接口预留
- **回测引擎骨架**：`BacktestEngine.run()` 当前返回空 `BacktestResult`，完整回测通过 `scripts/run_backtest.py` 手动编排
- **60/30 分钟入场级未实现**：当前用日线代替（Task 6 显式延期到实盘接入时）
- **监控告警为骨架**：`daily_data_quality_check` 返回占位 dict，未接入真实数据源
- **单次回测默认 5 只股票**：完整 57 只全量回测约 50 分钟，调试时建议用 `max_bars=500` 限制

---

## 10. 下一步建议

- 接入实盘数据源（akshare / tushare）
- 实现 60/30 分钟 K 线的入场级逻辑（替换 Task 16 中的日线简化）
- 完善 BacktestEngine.run() 的逐 K 线遍历逻辑
- 实现 `daily_data_quality_check` 接入真实公告数据
- 接入券商交易 API（需要先实现 `FuturesAdapter` 的完整成本计算）

---

**许可**：本仓库代码仅供学习和策略研究使用，不构成投资建议。
