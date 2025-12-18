"""
Structured logging configuration for The Gold Trader's Edge.
"""

import logging
import sys
from datetime import datetime
from typing import Optional
import json


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data

        return json.dumps(log_entry)


class ColoredFormatter(logging.Formatter):
    """Colored console formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"{color}[{timestamp}] {record.levelname:8}{self.RESET} "
        message += f"{record.name}: {record.getMessage()}"
        
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"
            
        return message


def setup_logging(
    level: str = "INFO",
    json_format: bool = False,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Setup structured logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Use JSON format (for production) or colored format (for dev)
        log_file: Optional file path to write logs

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("gold_trader")
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    logger.handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))

    if json_format:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(ColoredFormatter())

    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "gold_trader") -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


# Create default logger
logger = setup_logging()


class LoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds extra context."""

    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {})
        extra["extra_data"] = self.extra
        kwargs["extra"] = extra
        return msg, kwargs


def get_context_logger(context: dict) -> LoggerAdapter:
    """
    Get a logger with additional context.

    Args:
        context: Dictionary of context data to include in logs

    Returns:
        LoggerAdapter with context
    """
    return LoggerAdapter(logger, context)


# Convenience functions
def log_trade(
    action: str,
    direction: str,
    entry_price: float,
    stop_loss: float,
    take_profit: Optional[float] = None,
    rule_name: str = "",
    **kwargs
):
    """Log a trade action."""
    context_logger = get_context_logger({
        "action": action,
        "direction": direction,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "rule": rule_name,
        **kwargs
    })
    context_logger.info(f"Trade {action}: {direction} @ {entry_price}")


def log_signal(
    rule_name: str,
    direction: str,
    confidence: float,
    **kwargs
):
    """Log a signal generation."""
    context_logger = get_context_logger({
        "rule": rule_name,
        "direction": direction,
        "confidence": confidence,
        **kwargs
    })
    context_logger.info(f"Signal generated: {rule_name} - {direction} (conf: {confidence:.2f})")


def log_backtest(
    total_trades: int,
    win_rate: float,
    profit_factor: float,
    final_balance: float,
    **kwargs
):
    """Log backtest results."""
    context_logger = get_context_logger({
        "total_trades": total_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "final_balance": final_balance,
        **kwargs
    })
    context_logger.info(
        f"Backtest complete: {total_trades} trades, "
        f"{win_rate:.1f}% win rate, PF: {profit_factor:.2f}"
    )
