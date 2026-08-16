"""监控与日志（第 11 节）"""
import logging


def setup_logger(name: str, log_file: str, level: str = "INFO") -> logging.Logger:
    """初始化 logger（写入指定文件）"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))

    if not logger.handlers:
        handler = logging.FileHandler(log_file, encoding="utf-8")
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def log_signal(logger: logging.Logger, symbol: str, scene: str,
               c_total: float, confidence_tier: str):
    """记录信号"""
    logger.info(
        f"信号: {symbol} 场景={scene} C_总={c_total} 置信度={confidence_tier}"
    )


def log_trade(logger: logging.Logger, symbol: str, action: str,
              price: float, volume: int):
    """记录交易"""
    logger.info(
        f"交易: {symbol} {action} {volume}股 @{price:.2f}"
    )


def daily_data_quality_check(date: str) -> dict:
    """每日数据质量检查（11.8 节）"""
    return {
        "数据完整性": True,   # 实际接入数据源
        "异常价格": [],
        "停牌标的": [],
        "涨跌停标的": [],
        "ST标的": [],
    }