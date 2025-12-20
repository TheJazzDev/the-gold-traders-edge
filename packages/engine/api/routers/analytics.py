"""
Analytics router - Performance analytics endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from data.loader import GoldDataLoader
from signals.gold_strategy import GoldStrategy, create_strategy_function
from backtesting.engine import BacktestEngine

router = APIRouter()

# Rule name mapping for human-readable names
RULE_DISPLAY_NAMES = {
    'golden_retracement': 'Golden Retracement (61.8%)',
    'ath_breakout_retest': 'ATH Breakout Retest',
    'momentum_50': '50% Momentum',
    'rsi_divergence': 'RSI Divergence',
    'ema_crossover': 'EMA Crossover (9/21)',
    'london_breakout': 'London Session Breakout',
    'order_block': 'Order Block Retest',
    'vwap_deviation': 'VWAP Deviation',
    'bollinger_squeeze': 'Bollinger Band Squeeze',
}

# Valid rule IDs
VALID_RULE_IDS = set(RULE_DISPLAY_NAMES.keys())


class PerformanceSummary(BaseModel):
    """Performance summary model."""
    period: str
    timeframe: str
    total_signals: int
    winning_signals: int
    losing_signals: int
    win_rate: float
    profit_factor: float
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    avg_win: float
    avg_loss: float


class RulePerformance(BaseModel):
    """Rule performance model."""
    name: str
    total_signals: int
    win_rate: float
    profit_factor: float
    net_pnl: float
    avg_return: float


class TradeDetail(BaseModel):
    """Individual trade detail model."""
    id: int
    signal_name: str
    direction: str
    entry_time: str
    entry_price: float
    exit_time: Optional[str]
    exit_price: Optional[float]
    stop_loss: float
    take_profit: Optional[float]
    status: str
    pnl: float
    pnl_pct: float
    risk_reward: Optional[float]


@router.get("/summary", response_model=PerformanceSummary)
async def get_performance_summary(
    timeframe: str = Query("4h", description="Timeframe: 4h or 1d"),
    rules: Optional[str] = Query("golden_retracement,ath_breakout_retest,momentum_50", description="Comma-separated rule IDs")
):
    """
    Get overall strategy performance summary.

    Returns aggregated performance metrics for the trading strategy.
    """
    try:
        # Load data
        loader = GoldDataLoader()
        processed_dir = Path("data/processed")
        pattern = f"xauusd_{timeframe}_*.csv"
        matching_files = list(processed_dir.glob(pattern))

        if not matching_files:
            raise HTTPException(
                status_code=404,
                detail=f"No data available for timeframe {timeframe}"
            )

        data_file = sorted(matching_files)[-1]
        df = loader.load_from_csv(str(data_file))

        # Initialize strategy
        strategy = GoldStrategy()

        # Configure rules - accept rule IDs directly
        if rules:
            for rule in strategy.rules_enabled:
                strategy.rules_enabled[rule] = False

            for rule_id in rules.split(','):
                rule_id = rule_id.strip()
                if rule_id in VALID_RULE_IDS:
                    strategy.rules_enabled[rule_id] = True

        # Run backtest
        engine = BacktestEngine(initial_balance=10000, position_size_pct=2.0)
        result = engine.run(df=df, strategy_func=create_strategy_function(strategy))

        # Calculate return percentage
        net_profit = result.final_balance - result.initial_balance
        return_pct = (net_profit / result.initial_balance) * 100

        return PerformanceSummary(
            period="all",
            timeframe=timeframe,
            total_signals=result.total_trades,
            winning_signals=result.winning_trades,
            losing_signals=result.losing_trades,
            win_rate=result.win_rate,
            profit_factor=result.profit_factor,
            total_return_pct=return_pct,
            sharpe_ratio=result.sharpe_ratio,
            max_drawdown_pct=result.max_drawdown_pct,
            avg_win=result.avg_win,
            avg_loss=abs(result.avg_loss)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating performance: {str(e)}")


@router.get("/by-rule", response_model=List[RulePerformance])
async def get_performance_by_rule(
    timeframe: str = Query("4h", description="Timeframe: 4h or 1d"),
    rules: Optional[str] = Query("golden_retracement,ath_breakout_retest,momentum_50", description="Comma-separated rule IDs")
):
    """
    Get performance breakdown by individual rules.

    Returns performance metrics for each trading rule separately.
    """
    try:
        # Load data
        loader = GoldDataLoader()
        processed_dir = Path("data/processed")
        pattern = f"xauusd_{timeframe}_*.csv"
        matching_files = list(processed_dir.glob(pattern))

        if not matching_files:
            raise HTTPException(
                status_code=404,
                detail=f"No data available for timeframe {timeframe}"
            )

        data_file = sorted(matching_files)[-1]
        df = loader.load_from_csv(str(data_file))

        # Initialize strategy
        strategy = GoldStrategy()

        # Configure rules - accept rule IDs directly
        if rules:
            for rule in strategy.rules_enabled:
                strategy.rules_enabled[rule] = False

            for rule_id in rules.split(','):
                rule_id = rule_id.strip()
                if rule_id in VALID_RULE_IDS:
                    strategy.rules_enabled[rule_id] = True

        # Run backtest
        engine = BacktestEngine(initial_balance=10000, position_size_pct=2.0)
        result = engine.run(df=df, strategy_func=create_strategy_function(strategy))

        # Calculate performance by rule
        rule_stats = {}
        for trade in result.trades:
            rule = trade.signal_name
            if rule not in rule_stats:
                rule_stats[rule] = {
                    'count': 0,
                    'wins': 0,
                    'gross_profit': 0,
                    'gross_loss': 0,
                    'pnl': 0
                }

            rule_stats[rule]['count'] += 1
            rule_stats[rule]['pnl'] += trade.pnl

            if trade.pnl > 0:
                rule_stats[rule]['wins'] += 1
                rule_stats[rule]['gross_profit'] += trade.pnl
            else:
                rule_stats[rule]['gross_loss'] += abs(trade.pnl)

        # Build response
        performances = []
        for rule, stats in sorted(rule_stats.items(), key=lambda x: x[1]['pnl'], reverse=True):
            win_rate = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
            pf = stats['gross_profit'] / stats['gross_loss'] if stats['gross_loss'] > 0 else float('inf')
            avg_return = stats['pnl'] / stats['count'] if stats['count'] > 0 else 0

            # Use display name if available, otherwise use original
            display_name = RULE_DISPLAY_NAMES.get(rule, rule.replace('_', ' ').title())

            performances.append(RulePerformance(
                name=display_name,
                total_signals=stats['count'],
                win_rate=win_rate,
                profit_factor=pf if pf != float('inf') else 99.99,
                net_pnl=stats['pnl'],
                avg_return=avg_return
            ))

        return performances

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating rule performance: {str(e)}")


@router.get("/trades", response_model=List[TradeDetail])
async def get_trade_history(
    timeframe: str = Query("4h", description="Timeframe: 4h or 1d"),
    rules: Optional[str] = Query("golden_retracement,ath_breakout_retest,momentum_50", description="Comma-separated rule IDs")
):
    """
    Get individual trade history with entry, SL, TP details.

    Returns all trades executed during the backtest.
    """
    try:
        # Load data
        loader = GoldDataLoader()
        processed_dir = Path("data/processed")
        pattern = f"xauusd_{timeframe}_*.csv"
        matching_files = list(processed_dir.glob(pattern))

        if not matching_files:
            raise HTTPException(
                status_code=404,
                detail=f"No data available for timeframe {timeframe}"
            )

        data_file = sorted(matching_files)[-1]
        df = loader.load_from_csv(str(data_file))

        # Initialize strategy
        strategy = GoldStrategy()

        # Configure rules - accept rule IDs directly
        if rules:
            for rule in strategy.rules_enabled:
                strategy.rules_enabled[rule] = False

            for rule_id in rules.split(','):
                rule_id = rule_id.strip()
                if rule_id in VALID_RULE_IDS:
                    strategy.rules_enabled[rule_id] = True

        # Run backtest
        engine = BacktestEngine(initial_balance=10000, position_size_pct=2.0)
        result = engine.run(df=df, strategy_func=create_strategy_function(strategy))

        # Build trade details
        trades = []
        for trade in result.trades:
            # Calculate P&L percentage
            pnl_pct = (trade.pnl / (trade.entry_price * trade.position_size)) * 100 if trade.entry_price and trade.position_size else 0

            # Use display name if available
            display_name = RULE_DISPLAY_NAMES.get(trade.signal_name, trade.signal_name.replace('_', ' ').title())

            trades.append(TradeDetail(
                id=trade.id,
                signal_name=display_name,
                direction=trade.direction.value,
                entry_time=str(trade.entry_time),
                entry_price=trade.entry_price,
                exit_time=str(trade.exit_time) if trade.exit_time else None,
                exit_price=trade.exit_price,
                stop_loss=trade.stop_loss,
                take_profit=trade.take_profit,
                status=trade.status.value.replace('_', ' ').title(),
                pnl=trade.pnl,
                pnl_pct=pnl_pct,
                risk_reward=trade.risk_reward
            ))

        return trades

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving trade history: {str(e)}")
