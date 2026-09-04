"""
Regression coverage for stale setting metadata.

initialize_defaults() previously only inserted rows missing from
DEFAULT_SETTINGS and never touched existing ones. When a setting's meaning
changed in code (e.g. enabled_strategies became something the engine
actually reads every candle close, so it no longer needs a restart), an
already-seeded production row kept its old requires_restart/description/
etc metadata forever — confirmed live: after wiring enabled_strategies to
take effect immediately, the admin UI still showed "requires a service
restart" because the already-existing DB row's requires_restart was never
updated to match the new code default.

initialize_defaults() must now sync metadata columns (everything except the
user-set `value`) on existing rows to match DEFAULT_SETTINGS.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database.connection import DatabaseManager
from database.models import Base
from database.settings_models import Setting, SettingCategory
from database.settings_repository import SettingsRepository


def make_repo(tmp_path):
    db_manager = DatabaseManager(f"sqlite:///{tmp_path / 'metadata_sync.db'}")
    session_scope = db_manager.session_scope()
    session = session_scope.__enter__()
    Base.metadata.create_all(bind=session.get_bind())
    return session, session_scope


class TestSettingsMetadataSync:
    def test_existing_row_requires_restart_is_synced_to_code_default(self, tmp_path):
        session, scope = make_repo(tmp_path)
        try:
            # Simulate a row seeded under the old code, before
            # enabled_strategies became a live-applied setting.
            stale = Setting(
                key='enabled_strategies',
                category=SettingCategory.STRATEGIES,
                value='["order_block_retest"]',
                value_type='json',
                default_value='["momentum_equilibrium", "london_session_breakout", "golden_fibonacci", "ath_retest", "order_block_retest"]',
                description='List of enabled trading strategies',
                editable=True,
                requires_restart=True,  # stale — code now says False
            )
            session.add(stale)
            session.commit()

            repo = SettingsRepository(session)
            repo.initialize_defaults()

            refreshed = session.query(Setting).filter_by(key='enabled_strategies').first()
            assert refreshed.requires_restart is False
        finally:
            scope.__exit__(None, None, None)

    def test_user_set_value_is_preserved_across_metadata_sync(self, tmp_path):
        session, scope = make_repo(tmp_path)
        try:
            repo = SettingsRepository(session)
            repo.initialize_defaults()
            repo.set('enabled_strategies', ['order_block_retest'])

            # Re-running initialize_defaults (as happens on every worker/API
            # startup) must not clobber the user's chosen value.
            repo.initialize_defaults()

            refreshed = session.query(Setting).filter_by(key='enabled_strategies').first()
            assert refreshed.get_typed_value() == ['order_block_retest']
        finally:
            scope.__exit__(None, None, None)
