"""传统指标辅助层（第 5 节）

修正：
- 漏洞 N：斜率用 5 日变化率
- 漏洞 O：均线场景前置
- 漏洞 P：趋势市 RSI 奖励强势
- 漏洞 Q：上涨用 EMA20 代理
- 微瑕 12：阶梯打分微调
- 微瑕 13：MACD 上升量化
- 微瑕 14：仅做多策略下超买降权
"""
import pandas as pd
import numpy as np
from strategy.utils.indicators import calc_ema, calc_macd, calc_rsi


def _calc_ma_score(close: pd.Series, scene: str) -> float:
    """均线综合分（漏洞 O 场景前置）"""
    if len(close) < 120:
        return 0.5 if scene != "趋势市" else 0.3

    ema20 = calc_ema(close, 20).iloc[-1]
    ema60 = calc_ema(close, 60).iloc[-1]
    ema120 = calc_ema(close, 120).iloc[-1]

    # 趋势分（微瑕 12：阶梯调整）
    if ema20 > ema60 > ema120:
        trend_score = 1.0
    elif ema20 > ema60:
        trend_score = 0.7
    elif ema20 > ema120:
        trend_score = 0.5
    else:
        trend_score = 0.0

    # 斜率分（漏洞 N：5 日变化率）
    ema20_series = calc_ema(close, 20)
    if len(ema20_series) >= 5:
        slope = (ema20_series.iloc[-1] - ema20_series.iloc[-5]) / ema20_series.iloc[-5]
        slope_score = 1.0 if slope > 0.008 else (0.5 if slope > 0 else 0.0)
    else:
        slope_score = 0.5

    if scene == "趋势市":
        return 0.7 * trend_score + 0.3 * slope_score
    return 0.5  # 漏洞 O：非趋势市中性分


def _calc_macd_score(close: pd.Series, scene: str) -> float:
    """MACD 综合分（含微瑕 11 复用 + 微瑕 13 量化）"""
    _, _, hist = calc_macd(close)
    if len(hist) < 5:
        return 0.5

    # 位置分
    macd_pos_score = 1.0 if hist.iloc[-1] >= 0 else max(0, 1 + hist.iloc[-1] / 0.0001)

    # 方向分（微瑕 13：当前 > 前 1 根）
    direction_score = 1.0 if hist.iloc[-1] > hist.iloc[-2] else 0.5

    # 背离分（仅拐点市）
    div_score = 0.0
    if scene == "拐点市" and len(close) >= 60:
        recent_low = close.tail(20).min()
        prev_low = close.tail(40).head(20).min()
        if recent_low < prev_low and hist.tail(20).min() > hist.tail(40).head(20).min():
            div_score = 1.0

    return 0.5 * macd_pos_score + 0.3 * direction_score + 0.2 * div_score


def _calc_rsi_score(close: pd.Series, scene: str) -> float:
    """RSI 评分（漏洞 P + 微瑕 14）"""
    rsi = calc_rsi(close, 14)
    if len(rsi) < 5:
        return 0.5
    rsi_val = rsi.iloc[-1]

    if scene == "趋势市":
        # 漏洞 P：奖励强势
        if rsi_val >= 60: return 1.0
        if rsi_val >= 50: return 0.7
        return 0.3
    elif scene == "拐点市":
        # 微瑕 14：仅做多策略下超买降权
        if rsi_val <= 30: return 1.0
        if rsi_val >= 70: return 0.5
        if 40 <= rsi_val <= 60: return 0.5
        return 0.6
    else:
        if 40 <= rsi_val <= 60: return 0.5
        return 0.6


def _calc_volume_score(close: pd.Series, volume: pd.Series, scene: str) -> float:
    """量价评分（漏洞 Q 上涨量化）"""
    if len(volume) < 20:
        return 0.5

    avg_vol = volume.tail(20).mean()
    current_vol = volume.iloc[-1]
    current_close = close.iloc[-1]
    ema20 = calc_ema(close, 20).iloc[-1]

    # 漏洞 Q：上涨用 EMA20 代理
    price_up = current_close > ema20

    if scene == "趋势市":
        if current_vol > avg_vol * 1.5 and price_up:
            return 1.0
        elif current_vol < avg_vol * 0.8 and price_up:
            return 0.4
        return 0.6
    elif scene == "拐点市":
        # 拐点市地量加分
        if current_vol < avg_vol * 0.5:
            return max(0.5, 0.9)
        if current_vol > avg_vol * 2.0:
            return 0.8
        return 0.5
    else:  # 震荡市
        if current_vol > avg_vol * 2.0:
            return 0.8
        return 0.5


def calc_c_traditional(close: pd.Series, high: pd.Series, low: pd.Series,
                       volume: pd.Series, scene: str) -> dict:
    """C_传统 综合评分（场景自适应）"""
    if scene == "中阴态":
        return {"C_传统": 0.0, "均线_综合分": 0.5, "MACD_综合分": 0.0,
                "RSI_评分": 0.5, "量价_评分": 0.5}

    ma_score = _calc_ma_score(close, scene)
    macd_score = _calc_macd_score(close, scene)
    rsi_score = _calc_rsi_score(close, scene)
    vol_score = _calc_volume_score(close, volume, scene)

    if scene == "趋势市":
        c_traditional = 0.5 * ma_score + 0.3 * macd_score + 0.1 * rsi_score + 0.1 * vol_score
    elif scene == "震荡市":
        c_traditional = 0.3 * rsi_score + 0.3 * vol_score + 0.2 * macd_score + 0.2 * ma_score
    elif scene == "拐点市":
        c_traditional = 0.4 * macd_score + 0.3 * rsi_score + 0.3 * vol_score
    else:
        c_traditional = 0.0

    return {
        "C_传统": round(c_traditional, 4),
        "均线_综合分": ma_score,
        "MACD_综合分": macd_score,
        "RSI_评分": rsi_score,
        "量价_评分": vol_score,
    }