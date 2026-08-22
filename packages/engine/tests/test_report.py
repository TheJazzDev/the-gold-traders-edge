"""Tests for the on-demand performance report."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from report import build_report_text


class TestBuildReportText:
    def test_includes_all_key_numbers(self):
        stats = {
            'total_signals': 20,
            'tp_hits': 15,
            'sl_hits': 4,
            'expired': 1,
            'still_open': 0,
            'closed_manual': 0,
            'win_rate': 78.9,
            'avg_r_multiple': 1.2,
            'net_r_multiple': 22.8,
        }
        text = build_report_text(stats, days=7)

        assert "7" in text
        assert "20" in text
        assert "15" in text
        assert "4" in text
        assert "78.9" in text
        assert "22.8" in text
