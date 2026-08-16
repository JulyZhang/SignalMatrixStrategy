import logging
import pytest
from strategy.monitor.monitor import setup_logger, log_signal, log_trade


@pytest.fixture(autouse=True)
def _reset_test_logger():
    """Reset the shared 'test' logger between tests so each gets a fresh handler."""
    yield
    logger = logging.getLogger("test")
    logger.handlers.clear()


def test_setup_logger_creates_handler(tmp_path):
    log_file = tmp_path / "test.log"
    logger = setup_logger("test", str(log_file), level="INFO")
    assert len(logger.handlers) == 1

def test_log_signal_writes_format(tmp_path):
    log_file = tmp_path / "test.log"
    logger = setup_logger("test", str(log_file), level="INFO")
    log_signal(logger, "600519", "趋势市", 0.78, "高")

    content = log_file.read_text(encoding="utf-8")
    assert "600519" in content
    assert "趋势市" in content
    assert "C_总=0.78" in content

def test_log_trade_writes_format(tmp_path):
    log_file = tmp_path / "test_trade.log"
    logger = setup_logger("test_trade", str(log_file), level="INFO")
    log_trade(logger, "600519", "买入", 100.50, 1000)

    content = log_file.read_text(encoding="utf-8")
    assert "600519" in content
    assert "买入" in content
    assert "1000股" in content
    assert "@100.50" in content