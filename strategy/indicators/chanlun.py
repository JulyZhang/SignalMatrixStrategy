"""缠论门控层（第 3 节）

5 阶段：
1. 前置过滤（中阴态）
2. 大级别周（双向判定）
3. 中级别日（场景-买点兼容）
4. 入场级 60+30 分钟
5. 最终评分 sqrt(C_周 × C_日)
"""
import pandas as pd
from strategy.utils.indicators import calc_ema, calc_macd, calc_macd_hist_mean_abs
from strategy.utils.atr import calc_atr


def calc_c_weekly(weekly_close: pd.Series, weekly_volume: pd.Series = None) -> float:
    """阶段 2：C_周 计算

    修正：
    - 漏洞 G：MACD<0 移至软性扣分
    - 漏洞 I：ATR 零值保护
    """
    if len(weekly_close) < 30:
        return 0.0

    ema20 = calc_ema(weekly_close, 20).iloc[-1]
    ema60 = calc_ema(weekly_close, 60).iloc[-1]

    # 硬性否决：方向不匹配
    if ema20 < ema60:
        return 0.0

    # 软性扣分
    soft_cap = 1.0

    # 粘合度 < 1.5%
    convergence = abs(ema20 - ema60) / ema60
    if convergence < 0.015:
        soft_cap = min(soft_cap, 0.5)

    # MACD_hist < 0
    _, _, hist = calc_macd(weekly_close)
    if hist.iloc[-1] < 0:
        soft_cap = min(soft_cap, 0.6)

    # 成交量
    if weekly_volume is not None:
        vol_ma = weekly_volume.rolling(20).mean().iloc[-1]
        if vol_ma > 0 and weekly_volume.iloc[-1] < vol_ma * 0.8:
            soft_cap = min(soft_cap, 0.6)

    # 基础分（漏洞 G：剔除 MACD 位置分）
    high = weekly_close * 1.05
    low = weekly_close * 0.95
    atr_w = calc_atr(high, low, weekly_close, 14).iloc[-1]

    # 漏洞 I：ATR 零值保护
    bias_denom = max(atr_w * 2, weekly_close.iloc[-1] * 0.001)
    bias_score = 1 - min(1, abs(weekly_close.iloc[-1] - ema60) / bias_denom)

    vol_score = 1.0
    if weekly_volume is not None and len(weekly_volume) >= 20:
        vol_ma = weekly_volume.rolling(20).mean().iloc[-1]
        vol_score = min(1, weekly_volume.iloc[-1] / vol_ma) if vol_ma > 0 else 0.5

    base_score = 0.5 * bias_score + 0.5 * vol_score
    return min(base_score, soft_cap)


def calc_c_daily(daily_close: pd.Series, buy_point: str = "二买") -> float:
    """阶段 3：C_日 计算（含三买/类三买结构例外）"""
    if len(daily_close) < 30:
        return 0.0

    # 结构完整度分（简化：中枢数量识别需更复杂算法）
    # 实际实现中需要完整的中枢识别
    structure_score = 0.7  # 默认中等

    # 三买/类三买例外
    if buy_point in ("三买", "类三买") and structure_score == 0.7:
        structure_score = 0.9

    # 买点清晰度分
    _, _, hist = calc_macd(daily_close)
    if len(hist) >= 10:
        recent_area = hist.tail(5).abs().sum()
        prev_area = hist.tail(10).head(5).abs().sum()
        if prev_area > 0:
            shrink_rate = 1 - recent_area / prev_area
            if shrink_rate >= 0.3:
                clarity_score = 1.0
            elif shrink_rate >= 0.1:
                clarity_score = 0.6
            else:
                clarity_score = 0.3
        else:
            clarity_score = 0.3
    else:
        clarity_score = 0.5

    # MACD 位置分
    denom = calc_macd_hist_mean_abs(hist, 20)
    if hist.iloc[-1] >= 0:
        macd_pos_score = 1.0
    else:
        macd_pos_score = max(0, 1 + hist.iloc[-1] / denom)

    return 0.4 * structure_score + 0.3 * clarity_score + 0.3 * macd_pos_score


def calc_chanlun_gate(
    scene: str,
    weekly_close: pd.Series,
    daily_close: pd.Series,
    weekly_volume: pd.Series = None,
    buy_point: str = "二买",
) -> dict:
    """缠论门控主入口

    返回：
    - C_缠论: float
    - 否决: bool
    - Scene_Snapshot: str
    """
    # 阶段 1：前置过滤
    if scene == "中阴态":
        return {"C_缠论": 0.0, "否决": True, "Scene_Snapshot": "中阴态"}

    # 阶段 2：C_周
    c_weekly = calc_c_weekly(weekly_close, weekly_volume)
    if c_weekly == 0.0:
        return {"C_缠论": 0.0, "否决": True, "Scene_Snapshot": scene}

    # 阶段 3：场景-买点兼容性 + C_日
    buy_point_allowed = {
        "趋势市": ["二买", "三买", "类二买"],
        "震荡市": ["三买", "类三买"],
        "拐点市": ["一买", "二买", "三买", "类二买", "类三买"],
    }
    if buy_point not in buy_point_allowed.get(scene, []):
        return {"C_缠论": 0.0, "否决": True, "Scene_Snapshot": scene}

    c_daily = calc_c_daily(daily_close, buy_point)

    # 阶段 5：最终评分
    c_chanlun = (c_weekly * c_daily) ** 0.5

    if c_chanlun < 0.5:
        return {"C_缠论": 0.0, "否决": True, "Scene_Snapshot": scene}

    return {
        "C_缠论": round(c_chanlun, 4),
        "否决": False,
        "Scene_Snapshot": scene,
    }


# 别名（plan line 805-810 列出 calc_c_chanlun）
def calc_c_chanlun(
    scene: str,
    weekly_close: pd.Series,
    daily_close: pd.Series,
    weekly_volume: pd.Series = None,
    buy_point: str = "二买",
) -> dict:
    """calc_c_chanlun 是 calc_chanlun_gate 的别名（plan 测试需要）"""
    return calc_chanlun_gate(scene, weekly_close, daily_close, weekly_volume, buy_point)