"""
Risk Manager
Enforces risk management rules before trade execution
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from .mt5_config import MT5Config

logger = logging.getLogger(__name__)


@dataclass
class DailyStats:
    """Daily trading statistics"""
    date: datetime
    trades_opened: int = 0
    trades_closed: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    largest_loss: float = 0.0
    current_drawdown: float = 0.0


class RiskManager:
    """Manage trading risk and enforce limits"""

    def __init__(self, config: MT5Config):
        self.config = config
        self.daily_stats: Dict[str, DailyStats] = {}
        self.current_positions: List[Dict[str, Any]] = []
        self.initial_balance: Optional[float] = None

    def set_initial_balance(self, balance: float):
        """Set initial account balance for drawdown calculation"""
        self.initial_balance = balance
        logger.info(f"Initial balance set to: ${balance:.2f}")

    def can_open_position(
        self,
        account_balance: float,
        proposed_risk: float,
        signal: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a new position can be opened

        Args:
            account_balance: Current account balance
            proposed_risk: Risk amount for the proposed trade
            signal: Signal information (optional, for logging)

        Returns:
            Tuple[bool, Optional[str]]: (can_open, reason_if_not)
        """
        today = datetime.now().date().isoformat()

        # Check 1: Maximum concurrent positions
        if len(self.current_positions) >= self.config.max_positions:
            reason = f"Maximum positions reached ({self.config.max_positions})"
            logger.warning(f"Risk check failed: {reason}")
            return False, reason

        # Check 2: Daily loss limit
        if today in self.daily_stats:
            stats = self.daily_stats[today]
            daily_loss_pct = abs(stats.total_pnl) / account_balance if stats.total_pnl < 0 else 0

            if daily_loss_pct >= self.config.max_daily_loss:
                reason = f"Daily loss limit reached ({daily_loss_pct*100:.2f}% >= {self.config.max_daily_loss*100}%)"
                logger.warning(f"Risk check failed: {reason}")
                return False, reason

            # Check if adding this trade would exceed daily limit (worst case)
            potential_daily_loss = abs(stats.total_pnl) + proposed_risk
            potential_loss_pct = potential_daily_loss / account_balance

            if potential_loss_pct > self.config.max_daily_loss:
                reason = f"Proposed trade could exceed daily loss limit (potential: {potential_loss_pct*100:.2f}%)"
                logger.warning(f"Risk check failed: {reason}")
                return False, reason

        # Check 3: Risk per trade
        risk_pct = proposed_risk / account_balance
        if risk_pct > self.config.max_risk_per_trade:
            reason = f"Risk per trade too high ({risk_pct*100:.2f}% > {self.config.max_risk_per_trade*100}%)"
            logger.warning(f"Risk check failed: {reason}")
            return False, reason

        # Check 4: Account balance threshold (don't trade if balance too low)
        if self.initial_balance and account_balance < self.initial_balance * 0.5:
            reason = f"Account balance below 50% of initial (${account_balance:.2f} < ${self.initial_balance * 0.5:.2f})"
            logger.warning(f"Risk check failed: {reason}")
            return False, reason

        # All checks passed
        logger.info(
            f"Risk check PASSED:\n"
            f"  Current positions: {len(self.current_positions)}/{self.config.max_positions}\n"
            f"  Proposed risk: ${proposed_risk:.2f} ({risk_pct*100:.2f}%)\n"
            f"  Daily P&L: ${stats.total_pnl:.2f if today in self.daily_stats else 0:.2f}\n"
            f"  Account balance: ${account_balance:.2f}"
        )

        return True, None

    def register_position_opened(
        self,
        ticket: int,
        symbol: str,
        direction: str,
        lot_size: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        risk_amount: float
    ):
        """
        Register a new position opened

        Args:
            ticket: MT5 ticket number
            symbol: Trading symbol
            direction: LONG or SHORT
            lot_size: Position size in lots
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            risk_amount: Risk amount in account currency
        """
        position = {
            "ticket": ticket,
            "symbol": symbol,
            "direction": direction,
            "lot_size": lot_size,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_amount": risk_amount,
            "opened_at": datetime.now(),
            "status": "open"
        }

        self.current_positions.append(position)

        # Update daily stats
        today = datetime.now().date().isoformat()
        if today not in self.daily_stats:
            self.daily_stats[today] = DailyStats(date=datetime.now())

        self.daily_stats[today].trades_opened += 1

        logger.info(
            f"Position registered:\n"
            f"  Ticket: {ticket}\n"
            f"  {direction} {lot_size} lots of {symbol}\n"
            f"  Entry: {entry_price}, SL: {stop_loss}, TP: {take_profit}\n"
            f"  Risk: ${risk_amount:.2f}\n"
            f"  Total open positions: {len(self.current_positions)}"
        )

    def register_position_closed(
        self,
        ticket: int,
        close_price: float,
        pnl: float,
        pnl_pips: float,
        close_reason: str = "unknown"
    ):
        """
        Register a position closed

        Args:
            ticket: MT5 ticket number
            close_price: Closing price
            pnl: Profit/loss in account currency
            pnl_pips: Profit/loss in pips
            close_reason: Reason for closure (tp, sl, manual, etc.)
        """
        # Find and remove position
        position = None
        for i, pos in enumerate(self.current_positions):
            if pos["ticket"] == ticket:
                position = self.current_positions.pop(i)
                break

        if not position:
            logger.warning(f"Position {ticket} not found in tracking")
            return

        # Update daily stats
        today = datetime.now().date().isoformat()
        if today not in self.daily_stats:
            self.daily_stats[today] = DailyStats(date=datetime.now())

        stats = self.daily_stats[today]
        stats.trades_closed += 1
        stats.total_pnl += pnl

        if pnl > 0:
            stats.winning_trades += 1
        else:
            stats.losing_trades += 1
            if abs(pnl) > abs(stats.largest_loss):
                stats.largest_loss = pnl

        # Calculate current drawdown
        if self.initial_balance:
            current_balance = self.initial_balance + stats.total_pnl
            stats.current_drawdown = (self.initial_balance - current_balance) / self.initial_balance

        logger.info(
            f"Position closed:\n"
            f"  Ticket: {ticket}\n"
            f"  Close price: {close_price}\n"
            f"  P&L: ${pnl:.2f} ({pnl_pips:.1f} pips)\n"
            f"  Reason: {close_reason}\n"
            f"  Daily P&L: ${stats.total_pnl:.2f}\n"
            f"  Win/Loss today: {stats.winning_trades}/{stats.losing_trades}\n"
            f"  Open positions: {len(self.current_positions)}"
        )

    def get_position_by_ticket(self, ticket: int) -> Optional[Dict[str, Any]]:
        """Get position by ticket number"""
        for position in self.current_positions:
            if position["ticket"] == ticket:
                return position
        return None

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions"""
        return self.current_positions.copy()

    def get_daily_stats(self, date: Optional[str] = None) -> Optional[DailyStats]:
        """
        Get daily statistics

        Args:
            date: Date in ISO format (YYYY-MM-DD). If None, returns today's stats.

        Returns:
            DailyStats or None
        """
        if date is None:
            date = datetime.now().date().isoformat()

        return self.daily_stats.get(date)

    def get_weekly_stats(self) -> Dict[str, Any]:
        """Get statistics for the past 7 days"""
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)

        total_trades = 0
        total_wins = 0
        total_losses = 0
        total_pnl = 0.0

        for date_str, stats in self.daily_stats.items():
            date = datetime.fromisoformat(date_str).date()
            if week_ago <= date <= today:
                total_trades += stats.trades_closed
                total_wins += stats.winning_trades
                total_losses += stats.losing_trades
                total_pnl += stats.total_pnl

        win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0

        return {
            "period": "7_days",
            "total_trades": total_trades,
            "winning_trades": total_wins,
            "losing_trades": total_losses,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "avg_pnl_per_trade": total_pnl / total_trades if total_trades > 0 else 0
        }

    def is_daily_limit_reached(self) -> bool:
        """Check if daily loss limit has been reached"""
        today = datetime.now().date().isoformat()

        if today not in self.daily_stats:
            return False

        stats = self.daily_stats[today]

        if stats.total_pnl >= 0:  # No loss
            return False

        if not self.initial_balance:
            logger.warning("Initial balance not set, cannot check daily limit")
            return False

        current_balance = self.initial_balance + stats.total_pnl
        loss_pct = abs(stats.total_pnl) / self.initial_balance

        return loss_pct >= self.config.max_daily_loss

    def should_stop_trading(self, account_balance: float) -> Tuple[bool, Optional[str]]:
        """
        Check if trading should be stopped (emergency conditions)

        Args:
            account_balance: Current account balance

        Returns:
            Tuple[bool, str]: (should_stop, reason)
        """
        # Check 1: Daily loss limit
        if self.is_daily_limit_reached():
            return True, "Daily loss limit reached"

        # Check 2: Account balance too low
        if self.initial_balance and account_balance < self.initial_balance * 0.3:
            return True, f"Account balance critical (${account_balance:.2f} < 30% of initial)"

        # Check 3: Too many consecutive losses
        today = datetime.now().date().isoformat()
        if today in self.daily_stats:
            stats = self.daily_stats[today]
            if stats.losing_trades >= 5 and stats.winning_trades == 0:
                return True, "Too many consecutive losses (5+)"

        return False, None

    def reset_daily_stats(self):
        """Reset daily statistics (usually called at end of day)"""
        yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()

        # Keep only last 30 days of stats
        cutoff_date = (datetime.now().date() - timedelta(days=30)).isoformat()
        self.daily_stats = {
            date: stats
            for date, stats in self.daily_stats.items()
            if date >= cutoff_date
        }

        logger.info(f"Daily stats cleaned up. Kept {len(self.daily_stats)} days of history")

    def get_risk_summary(self, account_balance: float) -> Dict[str, Any]:
        """
        Get current risk management summary

        Args:
            account_balance: Current account balance

        Returns:
            Dict with risk metrics
        """
        today = datetime.now().date().isoformat()
        today_stats = self.daily_stats.get(today, DailyStats(date=datetime.now()))

        total_risk_exposure = sum(pos["risk_amount"] for pos in self.current_positions)
        risk_exposure_pct = (total_risk_exposure / account_balance * 100) if account_balance > 0 else 0

        daily_loss_pct = (abs(today_stats.total_pnl) / account_balance * 100) if today_stats.total_pnl < 0 else 0

        return {
            "open_positions": len(self.current_positions),
            "max_positions": self.config.max_positions,
            "positions_available": self.config.max_positions - len(self.current_positions),
            "total_risk_exposure": total_risk_exposure,
            "risk_exposure_pct": risk_exposure_pct,
            "daily_pnl": today_stats.total_pnl,
            "daily_loss_pct": daily_loss_pct,
            "daily_loss_limit_pct": self.config.max_daily_loss * 100,
            "daily_loss_remaining_pct": max(0, (self.config.max_daily_loss * 100) - daily_loss_pct),
            "trades_today": today_stats.trades_opened,
            "wins_today": today_stats.winning_trades,
            "losses_today": today_stats.losing_trades,
            "can_trade": not self.is_daily_limit_reached(),
        }
