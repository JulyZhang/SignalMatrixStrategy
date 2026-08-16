"""场景识别（第 2 节）：5 步顺序过滤器

优先级：中阴态 > 拐点 > 趋势 > 震荡 > 默认中阴态
"""
import pandas as pd
from strategy.utils.indicators import calc_ema, calc_macd

# 关键阈值（与设计文档第 2 节一致；修复后更严格）
MA_CONVERGENCE_THRESHOLD = 0.003   # 修复：原 0.005 太宽松，正常上涨初期也触发
VOLATILITY_DECLINE_RATIO = 0.5     # 修复：原 0.7 太宽松，慢牛也触发中阴态


def _check_zhongyintai(close: pd.Series, weekly_close: pd.Series) -> bool:
    """中阴态触发检查（修复后）：周线收敛 + 日线 ATR 衰减 + 横盘 fallback"""
    # 检查 1: 周线 MA 收敛度
    ema20_w = weekly_close.ewm(span=20, adjust=False).mean()
    ema60_w = weekly_close.ewm(span=60, adjust=False).mean()
    if len(ema20_w) > 0 and len(ema60_w) > 0:
        convergence = abs(ema20_w.iloc[-1] - ema60_w.iloc[-1]) / ema60_w.iloc[-1]
        if convergence < MA_CONVERGENCE_THRESHOLD:
            return True

    # 检查 2: 日线 ATR 下降
    if len(close) >= 70:
        high = close * 1.01
        low = close * 0.99
        atr_recent = _calc_atr_simple(high, low, close, 20)
        atr_long = _calc_atr_simple(high, low, close, 50)
        if atr_long > 0 and atr_recent / atr_long < VOLATILITY_DECLINE_RATIO:
            return True

    # 检查 3（新增 fallback）: 长期横盘 —— 20 日波幅 / 中位价 < 5%
    if len(close) >= 20:
        rolling_high = close.rolling(window=20).max().iloc[-1]
        rolling_low = close.rolling(window=20).min().iloc[-1]
        median_price = close.tail(20).median()
        if median_price > 0:
            range_ratio = (rolling_high - rolling_low) / median_price
            if range_ratio < 0.05:   # 20 日内波幅 < 5%
                return True

    return False


def _calc_atr_simple(high, low, close, period):
    """简化 ATR（用于波动率判定）"""
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean().iloc[-1]


def _check_guandian(close: pd.Series) -> bool:
    """拐点市判定（修复后）：主判定 + fallback 判定，任一即触发"""
    if len(close) < 60:
        return False
    _, _, hist = calc_macd(close)

    # 主判定：MACD_hist 长期负值后开始反转（修复：放宽周期与严格度）
    recent_hist = hist.tail(15)  # 修复：10 → 15
    if len(recent_hist) < 15:
        return False

    # 主判定条件 A：长期负值（≥ 10 期 < 0） + 最近 5 期反转（至少 3 期递增）
    negative_count = sum(1 for v in recent_hist.iloc[:-5] if v < 0)
    recent_5 = recent_hist.iloc[-5:]
    increasing_count = sum(1 for i in range(1, len(recent_5)) if recent_5.iloc[i] > recent_5.iloc[i-1])

    main_condition = (negative_count >= 10 and increasing_count >= 3)

    # Fallback 判定：MACD_hist 由负转正 + 价格短期反弹 ≥ 5%
    if not main_condition and len(close) >= 10:
        # MACD_hist 在最近 3 期内至少 1 次由负转正
        hist_recent_3 = hist.tail(3)
        macd_turn = any(
            hist_recent_3.iloc[i-1] < 0 and hist_recent_3.iloc[i] >= 0
            for i in range(1, len(hist_recent_3))
        )
        # 价格 5 日涨幅 ≥ 5%
        pct_change_5d = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5] if len(close) >= 5 else 0
        price_rebound = pct_change_5d >= 0.05

        if macd_turn and price_rebound:
            return True

    return main_condition


def _check_trending(close: pd.Series) -> bool:
    """趋势市判定：EMA20 > EMA60 + ADX 替代（用价格斜率）"""
    if len(close) < 30:
        return False
    ema20 = calc_ema(close, 20)
    ema60 = calc_ema(close, 60)
    if ema20.iloc[-1] <= ema60.iloc[-1]:
        return False
    # 斜率判定
    slope = (ema20.iloc[-1] - ema20.iloc[-5]) / ema20.iloc[-5]
    return slope > 0.005  # 0.5%


def _check_range(close: pd.Series) -> bool:
    """震荡市判定：中枢内 + 低斜率"""
    if len(close) < 30:
        return False
    ema20 = calc_ema(close, 20)
    ema60 = calc_ema(close, 60)
    # EMA 缠绕（金叉死叉交替）
    diff = (ema20 - ema60).dropna()
    if len(diff) < 20:
        return False
    signs = (diff > 0).astype(int).diff().abs().sum()
    return signs >= 2  # 至少 2 次交叉


def recognize_scene(daily_close: pd.Series, weekly_close: pd.Series = None) -> str:
    """场景识别主入口（5 步顺序过滤器）"""
    if weekly_close is None:
        weekly_close = daily_close.resample("W").last().dropna()

    # Step 1: 中阴态过滤（最优先）
    if _check_zhongyintai(daily_close, weekly_close):
        return "中阴态"

    # Step 2: 拐点优先
    if _check_guandian(daily_close):
        return "拐点市"

    # Step 3: 趋势判定
    if _check_trending(daily_close):
        return "趋势市"

    # Step 4: 震荡兜底
    if _check_range(daily_close):
        return "震荡市"

    # Step 5: 默认中阴态
    return "中阴态"