"""
Console Subscriber

Pretty-prints signals to console with colors and formatting.
"""

from datetime import datetime


class ConsoleSubscriber:
    """
    Subscriber that prints signals to console with nice formatting.

    Features:
    - Color-coded output (LONG=green, SHORT=red)
    - Clean, readable format
    - Optional verbose mode
    - Table-style presentation
    """

    # ANSI color codes
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

    def __init__(self, use_colors: bool = True, verbose: bool = True):
        """
        Initialize console subscriber.

        Args:
            use_colors: Enable colored output (default: True)
            verbose: Show full details (default: True)
        """
        self.use_colors = use_colors
        self.verbose = verbose
        self.signal_count = 0

    def __call__(self, signal):
        """
        Receive and print signal.

        This method is called by the signal generator when a new signal is published.

        Args:
            signal: ValidatedSignal instance
        """
        try:
            self.print_signal(signal)
        except Exception as e:
            print(f"Failed to print signal: {e}")

    def print_signal(self, signal):
        """
        Print signal with formatting.

        Args:
            signal: ValidatedSignal instance
        """
        self.signal_count += 1

        # Choose color based on direction
        if self.use_colors:
            direction_color = self.GREEN if signal.direction == "LONG" else self.RED
            reset = self.RESET
            bold = self.BOLD
            cyan = self.CYAN
            yellow = self.YELLOW
        else:
            direction_color = reset = bold = cyan = yellow = ""

        if self.verbose:
            # Full detailed output
            print(f"\n{bold}{'='*70}{reset}")
            print(f"{bold}{cyan}📊 TRADING SIGNAL #{self.signal_count}{reset}")
            print(f"{bold}{'='*70}{reset}")
            print(f"\n{bold}Direction:{reset} {direction_color}{bold}{signal.direction}{reset}")
            print(f"{bold}Strategy:{reset}  {signal.strategy_name}")
            print(f"{bold}Symbol:{reset}    {signal.symbol} ({signal.timeframe})")
            print(f"{bold}Time:{reset}      {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S %Z')}")

            print(f"\n{bold}{yellow}💰 Price Levels:{reset}")
            print(f"   Entry:        ${signal.entry_price:,.2f}")
            print(f"   Stop Loss:    ${signal.stop_loss:,.2f}")
            print(f"   Take Profit:  ${signal.take_profit:,.2f}")
            print(f"   Current:      ${signal.current_price:,.2f}")

            print(f"\n{bold}{yellow}📈 Risk Management:{reset}")
            print(f"   Risk:         {signal.risk_pips:.1f} pips")
            print(f"   Reward:       {signal.reward_pips:.1f} pips")
            print(f"   R:R Ratio:    1:{signal.risk_reward_ratio:.2f}")
            print(f"   Confidence:   {signal.confidence*100:.1f}%")

            if signal.notes:
                print(f"\n{bold}{yellow}📝 Notes:{reset} {signal.notes}")

            print(f"\n{bold}{'='*70}{reset}\n")

        else:
            # Compact one-line output
            timestamp = signal.timestamp.strftime('%Y-%m-%d %H:%M')
            print(
                f"{bold}[{timestamp}]{reset} "
                f"{direction_color}{bold}{signal.direction:5s}{reset} "
                f"@ ${signal.entry_price:,.2f} | "
                f"SL: ${signal.stop_loss:,.2f} | "
                f"TP: ${signal.take_profit:,.2f} | "
                f"R:R: 1:{signal.risk_reward_ratio:.2f} | "
                f"Conf: {signal.confidence*100:.0f}%"
            )

    def print_summary(self):
        """Print summary statistics."""
        print(f"\n{self.BOLD}{'='*70}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}📊 SIGNAL SUMMARY{self.RESET}")
        print(f"{self.BOLD}{'='*70}{self.RESET}")
        print(f"Total signals received: {self.signal_count}")
        print(f"{self.BOLD}{'='*70}{self.RESET}\n")

    def reset_count(self):
        """Reset signal counter."""
        self.signal_count = 0


if __name__ == "__main__":
    """Test console subscriber."""
    from signals.realtime_generator import ValidatedSignal
    import pandas as pd

    print("=" * 70)
    print("🧪 TESTING CONSOLE SUBSCRIBER")
    print("=" * 70)

    # Test verbose mode
    print("\n1. Testing VERBOSE mode...")
    subscriber_verbose = ConsoleSubscriber(use_colors=True, verbose=True)

    test_signal_long = ValidatedSignal(
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
        notes="Strong bullish momentum at 50% retracement",
        current_price=2650.50
    )

    subscriber_verbose.print_signal(test_signal_long)

    test_signal_short = ValidatedSignal(
        timestamp=pd.Timestamp.now(),
        symbol="XAUUSD",
        timeframe="4H",
        strategy_name="Momentum Equilibrium",
        direction="SHORT",
        entry_price=2680.00,
        stop_loss=2695.30,
        take_profit=2649.40,
        confidence=0.60,
        risk_pips=153.0,
        reward_pips=306.0,
        risk_reward_ratio=2.0,
        notes="Bearish reversal at resistance",
        current_price=2680.00
    )

    subscriber_verbose.print_signal(test_signal_short)

    # Test compact mode
    print("\n2. Testing COMPACT mode...")
    subscriber_compact = ConsoleSubscriber(use_colors=True, verbose=False)

    for i in range(5):
        direction = "LONG" if i % 2 == 0 else "SHORT"
        test_signal = ValidatedSignal(
            timestamp=pd.Timestamp.now(),
            symbol="XAUUSD",
            timeframe="4H",
            strategy_name="Momentum Equilibrium",
            direction=direction,
            entry_price=2650.00 + i * 10,
            stop_loss=2635.00 + i * 10,
            take_profit=2680.00 + i * 10,
            confidence=0.6 + i * 0.05,
            risk_pips=150.0,
            reward_pips=300.0,
            risk_reward_ratio=2.0,
            notes="",
            current_price=2650.00 + i * 10
        )
        subscriber_compact.print_signal(test_signal)

    # Print summary
    subscriber_verbose.print_summary()

    print("\n" + "=" * 70)
    print("✅ CONSOLE SUBSCRIBER TEST COMPLETE!")
    print("=" * 70)
