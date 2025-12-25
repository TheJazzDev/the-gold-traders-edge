"""
Telegram Subscriber

Sends validated signals to a Telegram bot/channel in real-time.
"""

import sys
from pathlib import Path
import logging
from datetime import datetime
from typing import Optional
import os

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use system environment variables

try:
    import requests
except ImportError:
    print("❌ Error: 'requests' library not found. Install with: pip install requests")
    requests = None

logger = logging.getLogger(__name__)


class TelegramSubscriber:
    """
    Subscriber that sends signals to Telegram.

    Features:
    - Sends formatted signal messages to Telegram chat/channel
    - Supports both bot token and chat ID configuration
    - Formats signals with emoji and clear structure
    - Handles different signal types (LONG/SHORT)
    - Non-blocking: doesn't fail if Telegram is unavailable
    """

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Initialize Telegram subscriber.

        Args:
            bot_token: Telegram Bot API token (from @BotFather)
            chat_id: Telegram chat/channel ID to send messages to
                    (can be user ID, group ID, or @channel_username)

        Environment Variables (if args not provided):
            TELEGRAM_BOT_TOKEN: Bot token
            TELEGRAM_CHAT_ID: Chat ID
        """
        # Get credentials from args or environment
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")

        # Validate configuration
        if not self.bot_token or not self.chat_id:
            logger.warning(
                "⚠️  Telegram credentials not configured. "
                "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables."
            )
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"✅ TelegramSubscriber initialized: Chat ID {self.chat_id}")

        # Telegram API base URL
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def __call__(self, signal):
        """
        Receive and send signal to Telegram.

        This method is called by the signal generator when a new signal is published.

        Args:
            signal: ValidatedSignal instance
        """
        if not self.enabled:
            logger.debug("Telegram subscriber disabled - skipping")
            return

        try:
            self.send_signal(signal)
        except Exception as e:
            # Non-blocking: log error but don't crash
            logger.error(f"Failed to send signal to Telegram: {e}", exc_info=True)

    def send_signal(self, validated_signal) -> bool:
        """
        Send validated signal to Telegram.

        Args:
            validated_signal: ValidatedSignal from signal generator

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        if requests is None:
            logger.error("Cannot send Telegram message: 'requests' library not installed")
            return False

        # Format signal message
        message = self._format_signal_message(validated_signal)

        # Send to Telegram
        try:
            response = requests.post(
                self.api_url,
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "HTML"
                },
                timeout=10
            )

            if response.status_code == 200:
                logger.info(
                    f"📱 Signal sent to Telegram: {validated_signal.direction} @ "
                    f"${validated_signal.entry_price:.2f}"
                )
                return True
            else:
                logger.error(
                    f"Telegram API error: {response.status_code} - {response.text}"
                )
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def _format_signal_message(self, signal) -> str:
        """
        Format signal as a pretty Telegram message with HTML formatting.

        Args:
            signal: ValidatedSignal instance

        Returns:
            Formatted message string
        """
        # Direction emoji
        direction_emoji = "🟢" if signal.direction == "LONG" else "🔴"
        arrow = "📈" if signal.direction == "LONG" else "📉"

        # Confidence indicator
        confidence_stars = "⭐" * int(signal.confidence * 5)

        # Calculate pip values
        risk_pips = abs(signal.entry_price - signal.stop_loss) / 0.1
        reward_pips = abs(signal.take_profit - signal.entry_price) / 0.1

        # Format timestamp
        time_str = signal.timestamp.strftime("%Y-%m-%d %H:%M UTC")

        # Build message
        message = f"""
{direction_emoji} <b>NEW {signal.direction} SIGNAL</b> {arrow}

<b>Symbol:</b> {signal.symbol}
<b>Strategy:</b> {signal.strategy_name}
<b>Timeframe:</b> {signal.timeframe}
<b>Time:</b> {time_str}

💰 <b>TRADE DETAILS</b>
├ Entry: ${signal.entry_price:.2f}
├ Stop Loss: ${signal.stop_loss:.2f}
├ Take Profit: ${signal.take_profit:.2f}

📊 <b>RISK MANAGEMENT</b>
├ Risk: {risk_pips:.1f} pips
├ Reward: {reward_pips:.1f} pips
├ R:R Ratio: 1:{signal.risk_reward_ratio:.2f}
├ Confidence: {signal.confidence:.0%} {confidence_stars}

{signal.notes if signal.notes else ""}
""".strip()

        return message

    def send_custom_message(self, message: str) -> bool:
        """
        Send a custom message to Telegram.

        Args:
            message: Message text to send

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        if requests is None:
            logger.error("Cannot send Telegram message: 'requests' library not installed")
            return False

        try:
            response = requests.post(
                self.api_url,
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "HTML"
                },
                timeout=10
            )

            return response.status_code == 200

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send custom message: {e}")
            return False

    def send_test_message(self) -> bool:
        """
        Send a test message to verify bot configuration.

        Returns:
            True if test successful, False otherwise
        """
        test_message = """
🤖 <b>Gold Trader's Edge - Signal Bot</b>

✅ Bot is connected and ready!

You will receive real-time trading signals here.
"""
        return self.send_custom_message(test_message.strip())


if __name__ == "__main__":
    """Test Telegram subscriber."""
    from signals.realtime_generator import ValidatedSignal
    import pandas as pd

    print("=" * 70)
    print("🧪 TESTING TELEGRAM SUBSCRIBER")
    print("=" * 70)

    # Create subscriber
    print("\n1. Creating Telegram subscriber...")
    subscriber = TelegramSubscriber()

    if not subscriber.enabled:
        print("\n⚠️  Telegram not configured!")
        print("Set these environment variables:")
        print("  export TELEGRAM_BOT_TOKEN='your_bot_token'")
        print("  export TELEGRAM_CHAT_ID='your_chat_id'")
        print("\nTo create a bot:")
        print("  1. Message @BotFather on Telegram")
        print("  2. Send /newbot and follow instructions")
        print("  3. Copy the bot token")
        print("  4. Get your chat ID from @userinfobot")
        exit(1)

    # Send test message
    print("\n2. Sending test message...")
    if subscriber.send_test_message():
        print("   ✅ Test message sent!")
    else:
        print("   ❌ Failed to send test message")
        exit(1)

    # Create a test signal
    print("\n3. Creating test LONG signal...")
    test_signal = ValidatedSignal(
        timestamp=pd.Timestamp.now(),
        symbol="XAUUSD",
        timeframe="4H",
        strategy_name="Momentum Equilibrium",
        direction="LONG",
        entry_price=2650.50,
        stop_loss=2635.20,
        take_profit=2681.10,
        confidence=0.75,
        risk_pips=153.0,
        reward_pips=306.0,
        risk_reward_ratio=2.0,
        notes="Test signal from Telegram subscriber",
        current_price=2650.50
    )

    # Send signal
    print("\n4. Sending LONG signal to Telegram...")
    if subscriber.send_signal(test_signal):
        print("   ✅ LONG signal sent!")
    else:
        print("   ❌ Failed to send LONG signal")

    # Create SHORT signal
    print("\n5. Creating test SHORT signal...")
    test_signal_short = ValidatedSignal(
        timestamp=pd.Timestamp.now(),
        symbol="XAUUSD",
        timeframe="4H",
        strategy_name="Momentum Equilibrium",
        direction="SHORT",
        entry_price=2650.50,
        stop_loss=2665.80,
        take_profit=2619.90,
        confidence=0.82,
        risk_pips=153.0,
        reward_pips=306.0,
        risk_reward_ratio=2.0,
        notes="Bearish momentum detected",
        current_price=2650.50
    )

    # Send SHORT signal
    print("\n6. Sending SHORT signal to Telegram...")
    if subscriber.send_signal(test_signal_short):
        print("   ✅ SHORT signal sent!")
    else:
        print("   ❌ Failed to send SHORT signal")

    print("\n" + "=" * 70)
    print("✅ TELEGRAM SUBSCRIBER TEST COMPLETE!")
    print("=" * 70)
    print("\n📱 Check your Telegram chat for the messages!")
