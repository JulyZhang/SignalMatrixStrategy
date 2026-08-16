"""标的筛选（第 9 节）

修正：
- 漏洞 AF：20 日窗口定义
- 🟩 额外发现：股价 ≥ 1 元
"""
from typing import List, Dict
from strategy.config import Config


def filter_universe(
    universe: List[str],
    prices: Dict[str, float],
    avg_turnovers: Dict[str, float],   # 过去 20 个交易日均成交额
    market_caps: Dict[str, float],
    listing_days: Dict[str, int] = None,
    st_list: set = None,
    suspended: set = None,
) -> List[str]:
    """标的筛选（漏洞 AF + 🟩 价格过滤）"""
    selected = []
    for symbol in universe:
        if st_list is not None and symbol in st_list:
            continue
        if suspended is not None and symbol in suspended:
            continue
        if prices.get(symbol, 0) < Config.MIN_PRICE:
            continue
        if avg_turnovers.get(symbol, 0) < Config.MIN_AVG_TURNOVER:
            continue
        if market_caps.get(symbol, 0) < Config.MIN_MARKET_CAP:
            continue
        if listing_days is not None and listing_days.get(symbol, 0) < Config.MIN_LISTING_DAYS:
            continue
        selected.append(symbol)

    return selected