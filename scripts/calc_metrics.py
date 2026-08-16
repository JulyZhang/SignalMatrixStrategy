"""回测绩效指标计算（第 10.8 节）"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from typing import List, Dict


def calc_metrics(trades: List[Dict], initial_capital: float = 1_000_000) -> dict:
    """计算回测绩效指标

    Args:
        trades: List of {"symbol", "date", "card"} dicts from run_backtest.main()
        initial_capital: 初始资金

    Returns:
        dict with basic metrics
    """
    if not trades:
        # 空 trades：键名与非空分支保持一致（修复提议中的 signal_distribution/scene_distribution 不一致）
        return {
            "total_signals": 0,
            "symbols_count": 0,
            "avg_confidence": 0.0,
            "max_confidence": 0.0,
            "min_confidence": 0.0,
            "scene_distribution": {},
            "confidence_tier_distribution": {},
        }

    # 基础统计
    symbols = set(t["symbol"] for t in trades)
    confidences = [t["card"].confidence for t in trades]
    confidence_tiers = [t["card"].confidence_tier for t in trades]

    # 按场景分布
    scenes = [t["card"].scene for t in trades]
    scene_dist = {s: scenes.count(s) for s in set(scenes)}

    # 按置信度档位分布
    tier_dist = {tier: confidence_tiers.count(tier) for tier in set(confidence_tiers)}

    return {
        "total_signals": len(trades),
        "symbols_count": len(symbols),
        "avg_confidence": sum(confidences) / len(confidences),
        "max_confidence": max(confidences),
        "min_confidence": min(confidences),
        "scene_distribution": scene_dist,
        "confidence_tier_distribution": tier_dist,
    }


def print_metrics(metrics: dict):
    """打印指标"""
    print("\n=== 回测绩效指标 ===")
    print(f"总信号数: {metrics['total_signals']}")
    print(f"涉及股票数: {metrics['symbols_count']}")
    print(f"平均置信度: {metrics['avg_confidence']:.4f}")
    print(f"置信度区间: [{metrics['min_confidence']:.4f}, {metrics['max_confidence']:.4f}]")
    print(f"\n场景分布:")
    for scene, count in sorted(metrics['scene_distribution'].items(), key=lambda x: -x[1]):
        pct = count / metrics['total_signals'] * 100
        print(f"  {scene}: {count} ({pct:.1f}%)")
    print(f"\n置信度档位分布:")
    for tier, count in sorted(metrics['confidence_tier_distribution'].items()):
        pct = count / metrics['total_signals'] * 100
        print(f"  {tier}: {count} ({pct:.1f}%)")


if __name__ == "__main__":
    # 示例用法：先跑回测，再算指标
    from scripts.run_backtest import main
    trades = main()
    metrics = calc_metrics(trades)
    print_metrics(metrics)
