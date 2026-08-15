"""Global configuration for the Signal Matrix Strategy.

All cross-module shared constants live here. Imported as:
    from strategy.config import Config
"""


class Config:
    """Single source of truth for tunable strategy parameters."""

    # ---- Indicator periods -------------------------------------------------
    ATR_PERIOD = 14

    # ---- Signal weights per market regime ----------------------------------
    # Keys: 趋势市 (trending), 震荡市 (range-bound), 拐点市 (turning point)
    WEIGHT_MATRIX = {
        "趋势市": {"缠论": 0.5, "SMC": 0.2, "传统": 0.3},
        "震荡市": {"缠论": 0.3, "SMC": 0.6, "传统": 0.1},
        "拐点市": {"缠论": 0.4, "SMC": 0.4, "传统": 0.2},
    }

    # ---- Confidence tiers (used to lookup position sizes) -----------------
    CONFIDENCE_TIERS = {
        "极高": 0.8,
        "高": 0.6,
        "中": 0.5,
        "低": 0.4,
    }

    POSITION_TIERS = {
        "极高": 0.10,
        "高": 0.07,
        "中": 0.05,
        "低": 0.03,
    }

    # ---- Chanlun rules -----------------------------------------------------
    # Hard veto: triggered by hard contradictory signals from chanlun
    CHANLUN_HARD_VETO = {"方向不匹配": True}
    # Soft caps: weekly-level soft-cap conditions that cap C_周 confidence
    CHANLUN_SOFT_CAPS = {
        "粘合度": 0.5,
        "MACD<0": 0.6,
        "成交量": 0.6,
    }
    # Per-regime chanlun buy-point allow/ban lists
    CHANLUN_BUYPOINTS = {
        "趋势市": {"allow": ["二买", "三买", "类二买"], "ban": ["一买"]},
        "震荡市": {"allow": ["三买", "类三买"], "ban": ["一买", "二买"]},
        "拐点市": {"allow": ["一买", "二买", "三买", "类二买", "类三买"], "ban": []},
    }

    # ---- SMC time decay ----------------------------------------------------
    # (bars since signal, multiplier). None = floor.
    SMC_TIME_DECAY = [(10, 1.0), (20, 0.8), (None, 0.5)]

    # ---- Slippage by liquidity tier ----------------------------------------
    SLIPPAGE_BY_LIQUIDITY = {"高": 0.0002, "中": 0.0005, "低": 0.001}

    # ---- Daily price limit (涨跌停) by board -------------------------------
    LIMIT_PCT = {
        "主板": 0.10,
        "创业板": 0.20,
        "科创板": 0.20,
        "ST": 0.05,
    }

    # ---- Transaction costs --------------------------------------------------
    COMMISSION_RATE = 0.0003        # 佣金（买卖双向）
    STAMP_TAX_SELL = 0.001          # 印花税（仅卖出）
    TRANSFER_FEE = 0.00001          # 过户费（买卖双向）

    # ---- Universe / liquidity filters --------------------------------------
    MIN_AVG_TURNOVER = 5e7          # 20日均成交额下限（元）
    MIN_MARKET_CAP = 3e9            # 总市值下限（元）
    MIN_LISTING_DAYS = 90           # 上市天数下限
    MIN_PRICE = 1.0                 # 最低股价（元，规避仙股）

    # ---- Risk ---------------------------------------------------------------
    RISK_FREE_RATE = 0.025          # 无风险利率（年化）
