"""主入口：整合所有模块，实现一次完整决策"""
from typing import Optional

import pandas as pd

from strategy.scoring.scene import recognize_scene
from strategy.indicators.chanlun import calc_chanlun_gate
from strategy.indicators.smc import calc_c_smc
from strategy.indicators.traditional import calc_c_traditional
from strategy.scoring.weighted import calc_weighted_score
from strategy.signals.expectation_card import build_expectation_card, validate_card
from strategy.utils.atr import calc_atr


def run_strategy_on_bar(
    symbol: str,
    daily_close: pd.Series,
    daily_high: pd.Series,
    daily_low: pd.Series,
    daily_open: pd.Series,   # 新增：SMC OB 需要真实 OHLC
    daily_volume: pd.Series,
    weekly_close: pd.Series,
    weekly_volume: pd.Series,
    current_bar: dict,
    buy_point: str = "二买",
) -> Optional["ExpectationCard"]:
    """对单根 bar 运行完整策略，返回期望值卡片或 None

    📌 决策流程：
    1. 场景识别
    2. 缠论门控
    3. SMC 行为
    4. 传统指标
    5. 三层加权
    6. 构建期望值卡片
    7. 校验
    """
    # 1. 场景识别
    scene = recognize_scene(daily_close, weekly_close)

    # 2. 缠论门控
    chanlun_result = calc_chanlun_gate(
        scene=scene,
        weekly_close=weekly_close,
        daily_close=daily_close,
        weekly_volume=weekly_volume,
        buy_point=buy_point,
    )
    if chanlun_result["否决"]:
        return None
    scene = chanlun_result["Scene_Snapshot"]   # 锁定

    # 3. SMC（用真实 OHLC）
    high = daily_high
    low = daily_low
    close = daily_close
    open_ = daily_open

    # 计算 ATR_30min（简化：用日线代替）
    atr_30 = calc_atr(high, low, close, 14).iloc[-1]

    smc_result = calc_c_smc(
        ohlc=pd.DataFrame({
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
        }),
        scene=scene,
        atr_30=max(atr_30, 0.001),  # 漏洞 I 零值保护
    )

    # 4. 传统指标
    trad_result = calc_c_traditional(close, high, low, daily_volume, scene)

    # 5. 三层加权
    weighted = calc_weighted_score(
        scene=scene,
        C_缠论=chanlun_result["C_缠论"],
        C_SMC=smc_result["C_SMC"],
        C_传统=trad_result["C_传统"],
    )
    if weighted["否决"]:
        return None

    # 6. 构建期望值卡片
    # 简化：使用 ATR × 2 作为止损空间
    atr_val = max(atr_30, close.iloc[-1] * 0.001)   # 漏洞 I 保护
    stop_loss = current_bar["close"] - atr_val * 1.5

    card = build_expectation_card(
        symbol=symbol,
        scene=scene,
        entry_price=current_bar["close"],
        stop_loss=stop_loss,
        smc_upper=smc_result.get("期望空间上沿", 0),
        confidence=weighted["C_总"],
        C_缠论=chanlun_result["C_缠论"],
        C_SMC=smc_result["C_SMC"],
        C_传统=trad_result["C_传统"],
        buy_point=buy_point,
    )

    # 7. 校验
    if not validate_card(card):
        return None

    return card
