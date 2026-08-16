"""分级仓位计算（第 8 节）

修正：
- 漏洞 Z：ATR_ratio 数据不足保护
"""
from strategy.utils.atr import calc_atr_mean
from strategy.config import Config


def calc_position_size(card, total_capital: float, atr_history: list) -> dict:
    """计算建议仓位金额

    📌 entry_strategy 直接复用第 7 节 card.entry_strategy
    """
    # 基础仓位
    base_pct = Config.POSITION_TIERS.get(card.confidence_tier, 0.03)

    # 中阴态降级（防御性）
    if card.scene == "中阴态":
        base_pct = min(base_pct, 0.07)

    # ATR 自适应缩放（漏洞 Z）
    import pandas as pd
    atr_series = pd.Series(atr_history) if atr_history else pd.Series([1.0])
    if len(atr_series) < 50:
        atr_ratio = 1.0
    else:
        atr_mean = calc_atr_mean(atr_series, 50)
        atr_ratio = atr_series.iloc[-1] / atr_mean if atr_mean > 0 else 1.0

    if atr_ratio > 1.5:
        base_pct *= 0.7
    elif atr_ratio > 1.2:
        base_pct *= 0.85

    final_pct = min(base_pct, 0.10)

    return {
        "amount": total_capital * final_pct,
        "pct": final_pct,
        "entry_strategy": card.entry_strategy,   # 复用第 7 节
    }