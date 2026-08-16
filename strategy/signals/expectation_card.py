"""期望值卡片（第 7 节）

修正：
- 漏洞 V：RR 场景自适应
- 漏洞 W：复用 SMC 边界
- 漏洞 X：字段赋值
- 漏洞 Y：胜率阶梯映射
"""
from dataclasses import dataclass
from datetime import datetime

from strategy.config import Config


@dataclass
class ExpectationCard:
    symbol: str
    timestamp: datetime
    scene: str

    entry_price: float
    tp1: float
    tp2: float
    tp3: float
    expect_space_1r: float
    expect_space_2r: float

    stop_loss: float
    risk_space: float

    confidence: float
    confidence_tier: str

    risk_reward_ratio: float
    expected_value: float

    entry_strategy: str
    buy_point: str

    C_缠论: float
    C_SMC: float
    C_传统: float


def _calc_tps(scene: str, entry: float, R: float, smc_upper: float) -> tuple:
    """根据场景计算 TP1/TP2/TP3"""
    if scene == "趋势市":
        tp1 = entry + 1.5 * R
        tp2 = entry + 3.0 * R
        tp3 = entry + 5.0 * R
    elif scene == "震荡市":
        tp1 = entry + 1.0 * R
        tp2 = entry + 1.5 * R
        tp3 = entry + 2.0 * R
    elif scene == "拐点市":
        tp1 = entry + 2.0 * R
        tp2 = entry + 3.5 * R
        tp3 = entry + 5.0 * R
    else:
        tp1 = entry + 1.0 * R
        tp2 = entry + 2.0 * R
        tp3 = entry + 3.0 * R

    # 漏洞 W：TP2 上限校验
    if smc_upper > 0 and tp2 > smc_upper:
        tp2 = smc_upper
    if smc_upper > 0 and tp3 > smc_upper * 1.5:
        tp3 = smc_upper * 1.5

    return tp1, tp2, tp3


def build_expectation_card(
    symbol: str,
    scene: str,
    entry_price: float,
    stop_loss: float,
    smc_upper: float = 0.0,
    confidence: float = 0.5,
    C_缠论: float = 0.5,
    C_SMC: float = 0.5,
    C_传统: float = 0.5,
    buy_point: str = "二买",
) -> ExpectationCard:
    """构建期望值卡片

    📌 漏洞 Y：胜率阶梯映射
    """
    risk_space = entry_price - stop_loss
    R = risk_space

    tp1, tp2, tp3 = _calc_tps(scene, entry_price, R, smc_upper)
    expect_space_1r = tp1 - entry_price
    expect_space_2r = tp2 - entry_price

    # 风险回报比
    rr = expect_space_1r / risk_space if risk_space > 0 else 0

    # 置信度档位
    tier = "低"
    for name, threshold in sorted(Config.CONFIDENCE_TIERS.items(),
                                    key=lambda x: -x[1]):
        if confidence >= threshold:
            tier = name
            break

    # 漏洞 Y：胜率阶梯映射（0.5~1.0 → 0.5~0.9）
    win_rate = min(0.9, 0.5 + (confidence - 0.5) * 0.8)

    # 期望值
    expected_value = win_rate * expect_space_1r - (1 - win_rate) * risk_space

    # 入场策略
    strategy_map = {
        "极高": "一次性",
        "高": "分批(60%→40%)",
        "中": "分批(50%→30%→20%)",
        "低": "试探仓(30%→70%)",
    }
    entry_strategy = strategy_map.get(tier, "试探仓(30%→70%)")

    return ExpectationCard(
        symbol=symbol,
        timestamp=datetime.now(),
        scene=scene,
        entry_price=entry_price,
        tp1=tp1,
        tp2=tp2,
        tp3=tp3,
        expect_space_1r=expect_space_1r,
        expect_space_2r=expect_space_2r,
        stop_loss=stop_loss,
        risk_space=risk_space,
        confidence=confidence,
        confidence_tier=tier,
        risk_reward_ratio=rr,
        expected_value=expected_value,
        entry_strategy=entry_strategy,
        buy_point=buy_point,
        C_缠论=C_缠论,
        C_SMC=C_SMC,
        C_传统=C_传统,
    )


_EPSILON_RR = 1e-9


def validate_card(card: ExpectationCard) -> bool:
    """最低有效性校验（漏洞 V 场景自适应）"""
    # 场景自适应最低 RR
    min_rr = 1.0 if card.scene == "震荡市" else 1.5

    return (
        card.risk_reward_ratio >= min_rr - _EPSILON_RR   # 浮点容差
        and card.confidence >= 0.5
        and card.expected_value > 0
    )