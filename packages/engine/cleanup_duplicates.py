#!/usr/bin/env python3
"""
Cleanup script to remove duplicate signals from database.
Keeps only the first occurrence of each unique signal.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from database.connection import DatabaseManager
from database.models import Signal
from sqlalchemy import and_
import os

def cleanup_duplicates():
    """Remove duplicate signals, keeping only the first occurrence of each."""

    database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/gold_signals')

    db_manager = DatabaseManager(database_url)

    with db_manager.get_session() as session:
        # Find all signals
        all_signals = session.query(Signal).order_by(Signal.created_at).all()

        # Track seen signals by their key characteristics
        seen = set()
        duplicates_to_delete = []

        for signal in all_signals:
            # Create a unique key for this signal
            key = (
                signal.timestamp,
                signal.symbol,
                signal.strategy_name,
                signal.direction.value if hasattr(signal.direction, 'value') else signal.direction,
                round(float(signal.entry_price), 2),
                round(float(signal.stop_loss), 2),
                round(float(signal.take_profit), 2)
            )

            if key in seen:
                # This is a duplicate
                duplicates_to_delete.append(signal)
                print(f"🗑️  Marking for deletion: ID {signal.id} - {signal.timeframe} {signal.strategy_name} {signal.direction} @ ${signal.entry_price:.2f} (created: {signal.created_at})")
            else:
                # First occurrence
                seen.add(key)
                print(f"✅ Keeping: ID {signal.id} - {signal.timeframe} {signal.strategy_name} {signal.direction} @ ${signal.entry_price:.2f} (created: {signal.created_at})")

        # Delete duplicates
        if duplicates_to_delete:
            print(f"\n📊 Summary:")
            print(f"   Total signals: {len(all_signals)}")
            print(f"   Unique signals: {len(seen)}")
            print(f"   Duplicates to delete: {len(duplicates_to_delete)}")

            response = input(f"\n⚠️  Delete {len(duplicates_to_delete)} duplicate signals? (yes/no): ")

            if response.lower() == 'yes':
                for signal in duplicates_to_delete:
                    session.delete(signal)
                session.commit()
                print(f"✅ Deleted {len(duplicates_to_delete)} duplicate signals!")
            else:
                print("❌ Cancelled - no signals deleted")
        else:
            print("\n✅ No duplicates found!")

if __name__ == "__main__":
    cleanup_duplicates()
