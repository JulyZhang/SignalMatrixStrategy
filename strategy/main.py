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
    # 计算 ATR_30min（先用于 MSS 时效，也用于 SMC）
    atr_30 = calc_atr(daily_high, daily_low, daily_close, 14).iloc[-1]
    atr_30 = max(atr_30, 0.001)  # 漏洞 I 零值保护

    # 增强 3：构造最近 5 根 K 线（用于 MSS 时效检测，仅二买/类二买强制）
    ohlc_recent = pd.DataFrame({
        "open": daily_open,
        "high": daily_high,
        "low": daily_low,
        "close": daily_close,
    }).tail(5)

    chanlun_result = calc_chanlun_gate(
        scene=scene,
        weekly_close=weekly_close,
        daily_close=daily_close,
        weekly_volume=weekly_volume,
        buy_point=buy_point,
        ohlc_recent=ohlc_recent,   # 增强 3
        atr_30=atr_30,             # 增强 3
    )
    if chanlun_result["否决"]:
        return None
    scene = chanlun_result["Scene_Snapshot"]   # 锁定

    # 3. SMC（用真实 OHLC）
    high = daily_high
    low = daily_low
    close = daily_close
    open_ = daily_open

    smc_result = calc_c_smc(
        ohlc=pd.DataFrame({
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
        }),
        scene=scene,
        atr_30=atr_30,  # 已在步骤 2 计算（含零值保护）
    )

    # 4. 传统指标
    trad_result = calc_c_traditional(close, high, low, daily_volume, scene)

    # 5. 三层加权（增强 1 + 增强 2：传入 current_price 和 daily_close）
    weighted = calc_weighted_score(
        scene=scene,
        C_缠论=chanlun_result["C_缠论"],
        C_SMC=smc_result["C_SMC"],
        C_传统=trad_result["C_传统"],
        current_price=current_bar["close"],   # 增强 1 + 增强 2
        daily_close=daily_close,               # 增强 1 + 增强 2
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
