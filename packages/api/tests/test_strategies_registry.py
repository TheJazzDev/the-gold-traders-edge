"""Tests for the per-symbol strategy listing shown in the admin UI —
pure logic, no DB/FastAPI needed (same pattern as test_worker_status.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from strategies_registry import STRATEGY_REGISTRY, build_strategies_list


class TestStrategyRegistry:
    def test_covers_all_three_symbols(self):
        assert set(STRATEGY_REGISTRY.keys()) == {'XAUUSD', 'GBPUSD', 'EURUSD'}

    def test_gbpusd_and_eurusd_share_the_same_rule_name(self):
        assert STRATEGY_REGISTRY['GBPUSD'] == {'asian_range_london_breakout': 'Asian Range London Breakout'}
        assert STRATEGY_REGISTRY['EURUSD'] == {'asian_range_london_breakout': 'Asian Range London Breakout'}


class TestBuildStrategiesList:
    def test_gold_entry_enabled_from_enabled_strategies(self):
        result = build_strategies_list(
            enabled_strategies=['order_block_retest'],
            enabled_forex_symbols=[],
            validation_by_symbol={},
        )
        gold_entry = next(r for r in result if r['symbol'] == 'XAUUSD')
        assert gold_entry['key'] == 'order_block_retest'
        assert gold_entry['enabled'] is True

    def test_gbpusd_entry_disabled_by_default(self):
        result = build_strategies_list(
            enabled_strategies=['order_block_retest'],
            enabled_forex_symbols=[],
            validation_by_symbol={},
        )
        gbp_entry = next(r for r in result if r['symbol'] == 'GBPUSD')
        assert gbp_entry['enabled'] is False

    def test_gbpusd_entry_enabled_when_listed(self):
        result = build_strategies_list(
            enabled_strategies=['order_block_retest'],
            enabled_forex_symbols=['GBPUSD'],
            validation_by_symbol={},
        )
        gbp_entry = next(r for r in result if r['symbol'] == 'GBPUSD')
        eur_entry = next(r for r in result if r['symbol'] == 'EURUSD')
        assert gbp_entry['enabled'] is True
        assert eur_entry['enabled'] is False

    def test_validation_stats_attached_per_symbol(self):
        result = build_strategies_list(
            enabled_strategies=['order_block_retest'],
            enabled_forex_symbols=['GBPUSD'],
            validation_by_symbol={
                'GBPUSD': {'asian_range_london_breakout': {'profit_factor': 1.58, 'total_trades': 47}},
            },
        )
        gbp_entry = next(r for r in result if r['symbol'] == 'GBPUSD')
        assert gbp_entry['profit_factor'] == 1.58
        assert gbp_entry['total_trades'] == 47

    def test_missing_validation_reports_none_not_a_crash(self):
        result = build_strategies_list(
            enabled_strategies=['order_block_retest'],
            enabled_forex_symbols=[],
            validation_by_symbol={},
        )
        gbp_entry = next(r for r in result if r['symbol'] == 'GBPUSD')
        assert gbp_entry['profit_factor'] is None
        assert gbp_entry['validated'] is False

    def test_returns_one_entry_per_registry_rule(self):
        result = build_strategies_list(
            enabled_strategies=['order_block_retest'],
            enabled_forex_symbols=[],
            validation_by_symbol={},
        )
        assert len(result) == 3  # order_block_retest, asian_range_london_breakout x2
