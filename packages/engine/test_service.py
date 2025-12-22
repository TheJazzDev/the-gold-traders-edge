#!/usr/bin/env python3
"""
Test Signal Service

Quick test to verify the signal service works correctly.
"""

import sys
from pathlib import Path
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.signal_service import SignalService, ServiceConfig


def test_configuration():
    """Test configuration loading."""
    print("\n" + "=" * 70)
    print("🧪 TEST 1: Configuration")
    print("=" * 70)

    config = ServiceConfig()

    assert config.datafeed_type in ['yahoo', 'mt5', 'metaapi'], "Invalid datafeed type"
    assert config.timeframe in ['1H', '4H', '1D'], "Invalid timeframe"
    assert config.min_rr_ratio >= 1.0, "Invalid R:R ratio"

    print(f"✅ datafeed_type: {config.datafeed_type}")
    print(f"✅ symbol: {config.symbol}")
    print(f"✅ timeframe: {config.timeframe}")
    print(f"✅ min_rr_ratio: {config.min_rr_ratio}")

    assert config.validate(), "Configuration validation failed"
    print("✅ Configuration validation passed")


def test_service_initialization():
    """Test service initialization."""
    print("\n" + "=" * 70)
    print("🧪 TEST 2: Service Initialization")
    print("=" * 70)

    service = SignalService()

    assert service.config is not None, "Config not initialized"
    assert not service.is_running, "Service should not be running initially"

    print("✅ Service created successfully")
    print("✅ Config initialized")
    print("✅ Initial state correct")


def test_service_start_stop():
    """Test service start/stop with minimal iterations."""
    print("\n" + "=" * 70)
    print("🧪 TEST 3: Service Start/Stop")
    print("=" * 70)

    # Set test environment variables
    os.environ['ENABLE_CONSOLE'] = 'false'  # Disable console output for cleaner test

    service = SignalService()

    print("Starting service for 1 iteration...")

    try:
        service.start(max_iterations=1)
        print("✅ Service started and stopped successfully")
    except Exception as e:
        print(f"❌ Service failed: {e}")
        raise

    # Check service state after stop
    assert not service.is_running, "Service should be stopped"
    print("✅ Service state correct after stop")

    # Check statistics were tracked
    assert service.generator is not None, "Generator not initialized"
    assert service.generator.total_candles_processed >= 1, "No candles processed"
    print(f"✅ Candles processed: {service.generator.total_candles_processed}")
    print(f"✅ Signals generated: {service.generator.total_signals_generated}")


def test_service_status():
    """Test service status reporting."""
    print("\n" + "=" * 70)
    print("🧪 TEST 4: Service Status")
    print("=" * 70)

    service = SignalService()

    # Status when stopped
    status = service.get_status()
    assert status['status'] == 'STOPPED', "Status should be STOPPED"
    print(f"✅ Status when stopped: {status['status']}")

    # Note: Testing running status would require async execution
    print("✅ Status reporting works")


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("🧪 TESTING SIGNAL SERVICE")
    print("=" * 70)

    tests = [
        ("Configuration", test_configuration),
        ("Service Initialization", test_service_initialization),
        ("Service Start/Stop", test_service_start_stop),
        ("Service Status", test_service_status),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n❌ TEST FAILED: {name}")
            print(f"   Error: {e}")
            failed += 1

    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST RESULTS")
    print("=" * 70)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")

    if failed == 0:
        print("\n✅ ALL TESTS PASSED!")
        print("=" * 70)
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
