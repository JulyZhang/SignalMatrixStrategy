"""三层加权评分（第 6 节）

修正：
- 漏洞 R：中阴态防御
- 漏洞 S：C_缠论 < 0.3 极端防御
- 漏洞 T：SMC 否决场景自适应
- 漏洞 U：一致性否决权重层筛选
- 微瑕 15：震荡市有效层放宽
- 微瑕 16：否决时 C_总 = 0
"""
from strategy.config import Config


def calc_weighted_score(scene: str, C_缠论: float, C_SMC: float, C_传统: float) -> dict:
    """三层加权评分主入口

    返回：C_总, 置信度档位, 否决
    """
    # 漏洞 R：中阴态防御
    if scene == "中阴态":
        return {"C_总": 0.0, "置信度档位": "低", "否决": True}

    # 漏洞 S：C_缠论 极端防御
    if scene != "拐点市" and C_缠论 < 0.3:
        return {"C_总": 0.0, "置信度档位": "低", "否决": True}

    # 漏洞 T：SMC 否决场景自适应
    smc_veto = {
        "震荡市": 0.3,
        "拐点市": 0.25,
        "趋势市": 0.15,
    }
    if C_SMC < smc_veto.get(scene, 0.3):
        return {"C_总": 0.0, "置信度档位": "低", "否决": True}

    # 加权计算
    w = Config.WEIGHT_MATRIX[scene]
    c_total = w["缠论"] * C_缠论 + w["SMC"] * C_SMC + w["传统"] * C_传统

    # 漏洞 U + 微瑕 15：一致性否决
    有效层 = [
        ("缠论", C_缠论, w["缠论"]),
        ("SMC", C_SMC, w["SMC"]),
        ("传统", C_传统, w["传统"]),
    ]
    有效层 = [(n, s, wt) for n, s, wt in 有效层 if wt >= 0.2 and s > 0]

    if 有效层:
        主驱动层 = max(有效层, key=lambda x: x[2])
        if 主驱动层[1] < 0.4:
            return {"C_总": 0.0, "置信度档位": "低", "否决": True}

        if scene == "震荡市":
            # 微瑕 15：震荡市双弱
            if C_缠论 < 0.4 and C_SMC < 0.4:
                return {"C_总": 0.0, "置信度档位": "低", "否决": True}
        else:
            # 其他场景：低分项 ≥ 2 且有效层 ≥ 2
            低分项数 = sum(1 for _, s, _ in 有效层 if s < 0.4)
            if len(有效层) >= 2 and 低分项数 >= 2:
                return {"C_总": 0.0, "置信度档位": "低", "否决": True}

    # 置信度档位
    tier = "低"
    for name, threshold in sorted(Config.CONFIDENCE_TIERS.items(),
                                    key=lambda x: -x[1]):
        if c_total >= threshold:
            tier = name
            break

    return {
        "C_总": round(c_total, 4),
        "置信度档位": tier,
        "否决": False,
    }
