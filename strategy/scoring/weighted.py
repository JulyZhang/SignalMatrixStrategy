"""三层加权评分（第 6 节）

修正：
- 漏洞 R：中阴态防御
- 漏洞 S：C_缠论 < 0.3 极端防御
- 漏洞 T：SMC 否决场景自适应
- 漏洞 U：一致性否决权重层筛选
- 微瑕 15：震荡市有效层放宽
- 微瑕 16：否决时 C_总 = 0

增强：
- 增强 1：历史阻力位降权（×0.7）
- 增强 2：乖离率约束（封顶"高"档）
"""
import pandas as pd

from strategy.config import Config
from strategy.utils.indicators import calc_ema


def _apply_resistance_penalty(c_total: float, current_price: float,
                              daily_close: pd.Series) -> float:
    """历史阻力位降权（增强 1）

    如果当前价格处于过去 1 年（252 根日线）滚动最高点的 85% 以上，
    对 C_总施加 ×0.7 折扣（控制追高风险，但不完全否决）。

    Args:
        c_total: 计算好的 C_总
        current_price: 当前 bar 收盘价
        daily_close: 历史日线收盘价序列

    Returns:
        降权后的 C_总（如果触发惩罚），或原 c_total
    """
    if len(daily_close) < 252:
        return c_total   # 数据不足不做惩罚

    rolling_max = daily_close.rolling(window=252).max().iloc[-1]
    if rolling_max <= 0:
        return c_total

    ratio = current_price / rolling_max
    if ratio > 0.85:
        return c_total * 0.7
    return c_total


def _apply_bias_constraint(c_total: float, current_price: float,
                           daily_close: pd.Series) -> float:
    """乖离率约束（增强 2）

    如果当前价大幅高于 EMA120（超过 30%），说明短期涨幅过大。
    封顶 C_总 = 0.79（"高"档上限），避免给出"极高"档位。

    Args:
        c_total: 计算好的 C_总
        current_price: 当前 bar 收盘价
        daily_close: 历史日线收盘价序列

    Returns:
        受约束的 C_总
    """
    if len(daily_close) < 120:
        return c_total   # 数据不足不约束

    ema120 = calc_ema(daily_close, 120).iloc[-1]
    if ema120 <= 0:
        return c_total

    bias_ratio = (current_price - ema120) / ema120
    if bias_ratio > 0.30:
        # 硬封顶到"高"档上限 0.79（小于 0.80 的"极高"门槛）
        return min(c_total, 0.79)
    return c_total


def calc_weighted_score(scene: str, C_缠论: float, C_SMC: float, C_传统: float,
                       current_price: float = None,
                       daily_close: pd.Series = None) -> dict:
    """三层加权评分主入口

    返回：C_总, 置信度档位, 否决

    增强参数：
        current_price: 当前 bar 收盘价（用于阻力位/乖离率约束）
        daily_close: 历史日线收盘价序列（用于阻力位/乖离率约束）
    """
    # 漏洞 R：中阴态防御
    if scene == "中阴态":
        return {"C_总": 0.0, "置信度档位": "低", "否决": True}

    # 漏洞 S：C_缠论 极端防御
    if scene != "拐点市" and C_缠论 < 0.3:
        return {"C_总": 0.0, "置信度档位": "低", "否决": True}

    # 漏洞 T：SMC 否决场景自适应
    smc_veto = {
        "震荡市": 0.3,
        "拐点市": 0.25,
        "趋势市": 0.15,
    }
    if C_SMC < smc_veto.get(scene, 0.3):
        return {"C_总": 0.0, "置信度档位": "低", "否决": True}

    # 加权计算
    w = Config.WEIGHT_MATRIX[scene]
    c_total = w["缠论"] * C_缠论 + w["SMC"] * C_SMC + w["传统"] * C_传统

    # 增强 1：历史阻力位降权（×0.7）
    if current_price is not None and daily_close is not None:
        c_total = _apply_resistance_penalty(c_total, current_price, daily_close)

    # 增强 2：乖离率约束（封顶"高"档 0.79）
    if current_price is not None and daily_close is not None:
        c_total = _apply_bias_constraint(c_total, current_price, daily_close)

    # 漏洞 U + 微瑕 15：一致性否决
    有效层 = [
        ("缠论", C_缠论, w["缠论"]),
        ("SMC", C_SMC, w["SMC"]),
        ("传统", C_传统, w["传统"]),
    ]
    有效层 = [(n, s, wt) for n, s, wt in 有效层 if wt >= 0.2 and s > 0]

    if 有效层:
        主驱动层 = max(有效层, key=lambda x: x[2])
        if 主驱动层[1] < 0.4:
            return {"C_总": 0.0, "置信度档位": "低", "否决": True}

        if scene == "震荡市":
            # 微瑕 15：震荡市双弱
            if C_缠论 < 0.4 and C_SMC < 0.4:
                return {"C_总": 0.0, "置信度档位": "低", "否决": True}
        else:
            # 其他场景：低分项 ≥ 2 且有效层 ≥ 2
            低分项数 = sum(1 for _, s, _ in 有效层 if s < 0.4)
            if len(有效层) >= 2 and 低分项数 >= 2:
                return {"C_总": 0.0, "置信度档位": "低", "否决": True}

    # 置信度档位
    tier = "低"
    for name, threshold in sorted(Config.CONFIDENCE_TIERS.items(),
                                    key=lambda x: -x[1]):
        if c_total >= threshold:
            tier = name
            break

    return {
        "C_总": round(c_total, 4),
        "置信度档位": tier,
        "否决": False,
    }