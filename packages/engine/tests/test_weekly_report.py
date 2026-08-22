"""Tests for the weekly Telegram report."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import run_multi_timeframe_service as svc_module


class TestSendWeeklyReport:
    def test_sends_formatted_report_via_telegram(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "fake-chat-id")

        service = svc_module.MultiTimeframeService.__new__(svc_module.MultiTimeframeService)
        service.database_url = "sqlite:///:memory:"
        service.telegram_subscriber = MagicMock()

        fake_stats = {
            'total_signals': 10, 'tp_hits': 6, 'sl_hits': 3, 'expired': 1,
            'still_open': 0, 'closed_manual': 0, 'win_rate': 66.7,
            'avg_r_multiple': 0.9, 'net_r_multiple': 8.1,
        }
        with patch.object(svc_module.SignalRepository, 'get_performance_stats', return_value=fake_stats):
            with patch("database.connection.DatabaseManager.session_scope"):
                service._send_weekly_report()

        service.telegram_subscriber.send_custom_message.assert_called_once()
        message = service.telegram_subscriber.send_custom_message.call_args[0][0]
        assert "Weekly" in message
        assert "66.7" in message
