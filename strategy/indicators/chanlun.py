"""缠论门控层（第 3 节）

5 阶段：
1. 前置过滤（中阴态）
2. 大级别周（双向判定）
3. 中级别日（场景-买点兼容）
4. 入场级 60+30 分钟
5. 最终评分 sqrt(C_周 × C_日)
"""
from dataclasses import dataclass
import pandas as pd
from strategy.utils.indicators import calc_ema, calc_macd, calc_macd_hist_mean_abs
from strategy.utils.atr import calc_atr
from strategy.indicators.smc import detect_mss_within_window


@dataclass
class Zhongshu:
    """缠论中枢"""
    start_idx: int          # 在原始价格序列中的起始索引
    end_idx: int            # 结束索引
    high: float             # ZG（中枢上沿）
    low: float              # ZD（下沿）
    direction: str          # 'up' (上升中枢) 或 'down' (下降中枢)
    type: str               # 'extension' (延伸) / 'new' (新中枢)


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


def _process_inclusion(highs: pd.Series, lows: pd.Series) -> pd.DataFrame:
    """处理 K 线包含关系，返回简化序列

    规则（向上走势）：
        若 i-1 的高点 ≤ i 的高点 AND i-1 的低点 ≥ i 的低点
        → i-1 被 i 包含，删除 i-1

    规则（向下走势）：
        若 i-1 的高点 ≥ i 的高点 AND i-1 的低点 ≤ i 的低点
        → i-1 被 i 包含，删除 i-1

    Returns:
        DataFrame with columns: high, low (索引对应原始 K 线位置)
    """
    n = len(highs)
    if n < 3:
        return pd.DataFrame({'high': highs, 'low': lows}, index=list(range(n)))

    # 初始方向假设：向上
    highs_arr = list(highs)
    lows_arr = list(lows)
    keep = [True] * n   # 是否保留

    direction = 'up'   # 初始向上

    i = 2
    while i < n:
        if not keep[i-1]:
            i += 1
            continue

        prev_high, prev_low = highs_arr[i-1], lows_arr[i-1]
        curr_high, curr_low = highs_arr[i], lows_arr[i]

        if direction == 'up':
            # 上升：curr 包含 prev
            if curr_high >= prev_high and curr_low <= prev_low:
                keep[i-1] = False   # 删除 prev
                # 不增加 i（下次检查相同位置）
                continue
            elif curr_high < prev_high and curr_low > prev_low:
                # 当前 K 线被前一根包含
                keep[i] = False
                i += 1
                continue
            elif curr_high < prev_high:
                # 当前 K 线高点 < 前一 K 线高点，方向可能反转
                direction = 'down'
        else:
            # 下降：prev 包含 curr
            if curr_high <= prev_high and curr_low >= prev_low:
                keep[i-1] = False
                continue
            elif curr_high > prev_high and curr_low < prev_low:
                # 当前 K 线包含前一根
                keep[i] = False
                i += 1
                continue
            elif curr_low > prev_low:
                direction = 'up'
        i += 1

    # 构建简化序列
    result_highs = []
    result_lows = []
    result_indices = []
    for idx in range(n):
        if keep[idx]:
            result_highs.append(highs_arr[idx])
            result_lows.append(lows_arr[idx])
            result_indices.append(idx)

    return pd.DataFrame({
        'high': result_highs,
        'low': result_lows,
    }, index=result_indices)


def _find_fractals(simplified: pd.DataFrame) -> pd.DataFrame:
    """在简化序列上识别顶/底分型（独立判定，标准缠论定义）

    顶分型：中K 高点 ≥ 左侧高点 AND 高点 ≥ 右侧高点（只看高点）
    底分型：中K 低点 ≤ 左侧低点 AND 低点 ≤ 右侧低点（只看低点）

    修复：之前是合并判定（中K同时高点最高+低点最低），过严导致识别太少
    """
    if len(simplified) < 3:
        return pd.DataFrame(columns=['idx', 'type', 'high', 'low'])

    fractals = []
    for i in range(1, len(simplified) - 1):
        prev = simplified.iloc[i-1]
        curr = simplified.iloc[i]
        next_ = simplified.iloc[i+1]

        # 顶分型：只看高点（标准缠论）
        if curr['high'] >= prev['high'] and curr['high'] >= next_['high']:
            fractals.append({
                'idx': simplified.index[i],
                'type': 'top',
                'high': curr['high'],
                'low': curr['low'],
            })
        # 底分型：只看低点（标准缠论）
        elif curr['low'] <= prev['low'] and curr['low'] <= next_['low']:
            fractals.append({
                'idx': simplified.index[i],
                'type': 'bottom',
                'high': curr['high'],
                'low': curr['low'],
            })

    return pd.DataFrame(fractals)


def _find_segments(fractals: pd.DataFrame, min_bars: int = 5) -> list:
    """从分型序列识别笔

    笔 = 底分型 → 顶分型（上升）或 顶分型 → 底分型（下降）
    中间至少 5 根 K 线（min_bars）

    Returns:
        List of segments: [{start_idx, end_idx, start_type, end_type, high, low}]
    """
    if len(fractals) < 2:
        return []

    segments = []
    for i in range(len(fractals) - 1):
        f1 = fractals.iloc[i]
        f2 = fractals.iloc[i + 1]

        # 必须交替（底→顶 或 顶→底）
        if f1['type'] == f2['type']:
            continue

        # 中间至少 min_bars 根
        if f2['idx'] - f1['idx'] < min_bars:
            continue

        # 上升笔（底→顶）：end 高于 start
        # 下降笔（顶→底）：end 低于 start
        if f1['type'] == 'bottom' and f2['high'] > f1['high']:
            segments.append({
                'start_idx': f1['idx'],
                'end_idx': f2['idx'],
                'start_type': 'bottom',
                'end_type': 'top',
                'high': f2['high'],
                'low': f1['low'],
            })
        elif f1['type'] == 'top' and f2['low'] < f1['low']:
            segments.append({
                'start_idx': f1['idx'],
                'end_idx': f2['idx'],
                'start_type': 'top',
                'end_type': 'bottom',
                'high': f1['high'],
                'low': f2['low'],
            })

    return segments


def _find_zhongshus(segments: list) -> list:
    """从笔序列识别中枢

    中枢 = 连续 3 笔（上升-下降-上升 或 下降-上升-下降）的重叠区间

    Returns:
        List of Zhongshu
    """
    if len(segments) < 3:
        return []

    zhongshus = []
    i = 0
    while i <= len(segments) - 3:
        s1, s2, s3 = segments[i], segments[i+1], segments[i+2]

        # 形态：s1↑s2↓s3↑ 或 s1↓s2↑s3↓
        direction_ok = (
            (s1['end_type'] == 'top' and s2['end_type'] == 'bottom' and s3['end_type'] == 'top') or
            (s1['end_type'] == 'bottom' and s2['end_type'] == 'top' and s3['end_type'] == 'bottom')
        )
        if not direction_ok:
            i += 1
            continue

        # 重叠区间
        # 上升中枢：max(s1.low, s2.low, s3.low) ≤ min(s1.high, s2.high, s3.high)
        # ZG = min(三个 high), ZD = max(三个 low)
        highs = [s1['high'], s2['high'], s3['high']]
        lows = [s1['low'], s2['low'], s3['low']]

        ZG = min(highs)
        ZD = max(lows)

        if ZG <= ZD:   # 必须有重叠
            i += 1
            continue

        direction = 'up' if s1['end_type'] == 'bottom' else 'down'

        zhongshus.append(Zhongshu(
            start_idx=s1['start_idx'],
            end_idx=s3['end_idx'],
            high=ZG,
            low=ZD,
            direction=direction,
            type='new',
        ))

        # 中枢可延伸：下一笔如果与当前中枢重叠，可扩展
        j = i + 3
        while j < len(segments):
            next_seg = segments[j]
            # 检查是否与当前中枢重叠
            if max(next_seg['low'], ZD) <= min(next_seg['high'], ZG):
                # 延伸：更新 end_idx 和高低点
                ZG = min(ZG, next_seg['high'])
                ZD = max(ZD, next_seg['low'])
                zhongshus[-1] = Zhongshu(
                    start_idx=zhongshus[-1].start_idx,
                    end_idx=next_seg['end_idx'],
                    high=ZG,
                    low=ZD,
                    direction=direction,
                    type='extension',
                )
                j += 1
            else:
                break

        i = j   # 跳过已用笔

    return zhongshus


def detect_zhongshu(highs: pd.Series, lows: pd.Series, lookback: int = 120) -> list:
    """缠论中枢识别（使用真实 OHLC）

    算法：
    1. 处理包含关系 → 特征序列
    2. 识别顶/底分型
    3. 识别笔（≥5 根 K 线）
    4. 识别中枢（连续 3 笔重叠区间）

    Args:
        highs: 最高价序列
        lows: 最低价序列
        lookback: 最大回看窗口（默认 120 根 K 线 ≈ 半年）

    Returns:
        中枢列表，按时间正序

    Raises:
        ValueError: highs 和 lows 长度不一致
    """
    if len(highs) != len(lows):
        raise ValueError("highs 和 lows 长度必须一致")
    if len(highs) < 20:
        return []

    # 取最近 lookback 根
    h = highs.tail(lookback).reset_index(drop=True)
    l = lows.tail(lookback).reset_index(drop=True)

    # Step 1: 包含关系
    simplified = _process_inclusion(h, l)

    # Step 2: 分型
    fractals = _find_fractals(simplified)

    # Step 3: 笔
    segments = _find_segments(fractals, min_bars=5)

    # Step 4: 中枢
    zhongshus = _find_zhongshus(segments)

    return zhongshus


def calc_chanlun_gate(
    scene: str,
    weekly_close: pd.Series,
    daily_close: pd.Series,
    weekly_volume: pd.Series = None,
    buy_point: str = "二买",
    ohlc_recent: pd.DataFrame = None,
    atr_30: float = 1.0,
) -> dict:
    """缠论门控主入口

    返回：
    - C_缠论: float
    - 否决: bool
    - Scene_Snapshot: str

    增强参数：
        ohlc_recent: 最近 N 根 K 线（含 OHLC），用于增强 3 的 MSS 时效检查
        atr_30: 30 分钟 ATR（用于 MSS 时效判断）
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

    # 阶段 4：入场级 MSS 时效（增强 3）
    # 一买不限 MSS（底部反转 MSS 滞后），三买/类三买不限 MSS
    # 仅二买/类二买要求 MSS 在最近 5 根 K 线内
    if ohlc_recent is not None and buy_point in ("二买", "类二买"):
        if not detect_mss_within_window(ohlc_recent, atr_30, buy_point, window=5):
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