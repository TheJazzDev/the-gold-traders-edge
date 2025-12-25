#!/usr/bin/env python3
"""
Quick script to check signals in Railway PostgreSQL database
"""
import psycopg2
from datetime import datetime

# Railway DATABASE_URL
DATABASE_URL = "postgresql://postgres:WuOXHUmfceYvlbNuyUrhAsQgJPmFyhJv@postgres.railway.internal:5432/railway"

# For local testing, use the public URL (get from Railway dashboard)
# Replace this with your actual public connection string from Railway
# DATABASE_URL = "postgresql://postgres:password@<your-railway-host>:5432/railway"

print("=" * 80)
print("🔍 CHECKING SIGNALS IN DATABASE")
print("=" * 80)

try:
    # Connect to database
    print("\n📡 Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Check if signals table exists
    print("\n1. Checking if 'signals' table exists...")
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'signals';
    """)
    table_exists = cursor.fetchone()

    if not table_exists:
        print("   ❌ 'signals' table does NOT exist!")
        print("   The database schema might not be initialized.")
    else:
        print("   ✅ 'signals' table exists")

        # Count total signals
        print("\n2. Counting total signals...")
        cursor.execute("SELECT COUNT(*) FROM signals;")
        total_count = cursor.fetchone()[0]
        print(f"   Total signals in database: {total_count}")

        # Get recent signals
        print("\n3. Fetching last 10 signals...")
        cursor.execute("""
            SELECT id, timestamp, symbol, timeframe, strategy_name,
                   direction, entry_price, stop_loss, take_profit, status
            FROM signals
            ORDER BY timestamp DESC
            LIMIT 10;
        """)
        signals = cursor.fetchall()

        if signals:
            print(f"   Found {len(signals)} signal(s):\n")
            for signal in signals:
                signal_id, timestamp, symbol, timeframe, strategy, direction, entry, sl, tp, status = signal
                print(f"   ID: {signal_id}")
                print(f"   Time: {timestamp}")
                print(f"   {symbol} {timeframe} | {strategy}")
                print(f"   {direction} @ ${entry:.2f} | SL: ${sl:.2f} | TP: ${tp:.2f}")
                print(f"   Status: {status}")
                print(f"   {'-' * 70}")
        else:
            print("   ⚠️  No signals found in database")
            print("   This could mean:")
            print("   - Signals haven't been generated yet (markets closed)")
            print("   - Duplicate filter is blocking all signals")
            print("   - Database subscriber isn't saving signals")

        # Check signals by timeframe
        print("\n4. Signals grouped by timeframe...")
        cursor.execute("""
            SELECT timeframe, COUNT(*) as count
            FROM signals
            GROUP BY timeframe
            ORDER BY count DESC;
        """)
        timeframe_counts = cursor.fetchall()

        if timeframe_counts:
            for tf, count in timeframe_counts:
                print(f"   {tf:>4} | {count:>3} signals")
        else:
            print("   No signals to group")

        # Check signals by strategy
        print("\n5. Signals grouped by strategy...")
        cursor.execute("""
            SELECT strategy_name, COUNT(*) as count
            FROM signals
            GROUP BY strategy_name
            ORDER BY count DESC;
        """)
        strategy_counts = cursor.fetchall()

        if strategy_counts:
            for strategy, count in strategy_counts:
                print(f"   {strategy:<30} | {count:>3} signals")
        else:
            print("   No signals to group")

    # Close connection
    cursor.close()
    conn.close()

    print("\n" + "=" * 80)
    print("✅ DATABASE CHECK COMPLETE")
    print("=" * 80)

except psycopg2.OperationalError as e:
    print(f"\n❌ Connection Error: {e}")
    print("\nThis script needs to run from a location that can access Railway's internal network.")
    print("Try running it from within the Railway container or use the public connection URL.")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n")
