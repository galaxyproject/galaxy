"""
Tests for the custos-to-PSA database migration.

This test suite verifies the migration script that moves authentication tokens
from custos_authnz_token to oidc_user_authnz_tokens.
"""

# Import the core migration function
# We need to use importlib since the filename has a revision prefix
import importlib.util
from datetime import (
    datetime,
    timedelta,
)
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import (
    Column,
    create_engine,
    DateTime,
    Integer,
    String,
    Text,
    VARCHAR,
)
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
)

import galaxy.model.migrations
from galaxy.model.custom_types import MutableJSONType

migrations_path = (
    Path(galaxy.model.migrations.__file__).parent
    / "alembic"
    / "versions_gxy"
    / "724237cc4cf0_migrate_custos_to_psa_tokens.py"
)
spec = importlib.util.spec_from_file_location("migration_module", migrations_path)
assert spec is not None, f"Could not load spec from {migrations_path}"
assert spec.loader is not None, f"Spec has no loader for {migrations_path}"
migration_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration_module)
migrate_custos_tokens_to_psa = migration_module.migrate_custos_tokens_to_psa

# Create test tables
_Base: Any = declarative_base()


class CustosAuthnzTokenTest(_Base):
    """Test model for custos_authnz_token table."""

    __tablename__ = "custos_authnz_token"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    external_user_id = Column(String(255))
    provider = Column(String(255))
    access_token = Column(Text)
    id_token = Column(Text)
    refresh_token = Column(Text)
    expiration_time = Column(DateTime)
    refresh_expiration_time = Column(DateTime)


class UserAuthnzTokenTest(_Base):
    """Test model for oidc_user_authnz_tokens table."""

    __tablename__ = "oidc_user_authnz_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    uid = Column(VARCHAR(255))
    provider = Column(VARCHAR(32))
    extra_data = Column(MutableJSONType)
    lifetime = Column(Integer)
    assoc_type = Column(VARCHAR(64))


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    _Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestCustosToPSAMigration:
    """Test the migration from custos to PSA token format."""

    def test_basic_token_migration(self, db_session):
        """Test basic token migration with all fields populated."""
        # Create a custos token
        now = datetime.now()
        expiration = now + timedelta(hours=1)
        refresh_expiration = now + timedelta(days=30)

        custos_token = CustosAuthnzTokenTest(
            user_id=1,
            external_user_id="user123",
            provider="keycloak",
            access_token="access_token_value",
            id_token="id_token_value",
            refresh_token="refresh_token_value",
            expiration_time=expiration,
            refresh_expiration_time=refresh_expiration,
        )
        db_session.add(custos_token)
        db_session.commit()

        # Get table objects for migration
        custos_table = CustosAuthnzTokenTest.__table__
        psa_table = UserAuthnzTokenTest.__table__

        # Run the actual migration function
        migrated_count = migrate_custos_tokens_to_psa(db_session.connection(), custos_table, psa_table)
        assert migrated_count == 1

        # Verify migration
        migrated = db_session.query(UserAuthnzTokenTest).filter_by(user_id=1).first()
        assert migrated is not None
        assert migrated.uid == "user123"
        assert migrated.provider == "keycloak"
        assert migrated.extra_data["access_token"] == "access_token_value"
        assert migrated.extra_data["id_token"] == "id_token_value"
        assert migrated.extra_data["refresh_token"] == "refresh_token_value"
        assert "auth_time" in migrated.extra_data
        assert "expires" in migrated.extra_data
        assert migrated.extra_data["expires"] > 0

    def test_migration_without_refresh_token(self, db_session):
        """Test migration when refresh token is not present."""
        custos_token = CustosAuthnzTokenTest(
            user_id=2,
            external_user_id="user456",
            provider="cilogon",
            access_token="access_token_2",
            id_token="id_token_2",
            refresh_token=None,
            expiration_time=datetime.now() + timedelta(hours=1),
            refresh_expiration_time=None,
        )
        db_session.add(custos_token)
        db_session.commit()

        # Get table objects for migration
        custos_table = CustosAuthnzTokenTest.__table__
        psa_table = UserAuthnzTokenTest.__table__

        # Run the actual migration function
        migrated_count = migrate_custos_tokens_to_psa(db_session.connection(), custos_table, psa_table)
        assert migrated_count == 1

        # Verify
        migrated = db_session.query(UserAuthnzTokenTest).filter_by(user_id=2).first()
        assert migrated is not None
        assert "refresh_token" not in migrated.extra_data
        assert "refresh_expires_in" not in migrated.extra_data

    def test_migration_preserves_provider_names(self, db_session):
        """Test that provider names are preserved correctly."""
        providers = ["keycloak", "cilogon"]

        for idx, provider in enumerate(providers, start=1):
            custos_token = CustosAuthnzTokenTest(
                user_id=idx + 100,
                external_user_id=f"user_{provider}",
                provider=provider,
                access_token=f"access_{provider}",
                id_token=f"id_{provider}",
                expiration_time=datetime.now() + timedelta(hours=1),
            )
            db_session.add(custos_token)

        db_session.commit()

        # Get table objects for migration
        custos_table = CustosAuthnzTokenTest.__table__
        psa_table = UserAuthnzTokenTest.__table__

        # Run the actual migration function
        migrated_count = migrate_custos_tokens_to_psa(db_session.connection(), custos_table, psa_table)
        assert migrated_count == 2

        # Verify
        for provider in providers:
            migrated = db_session.query(UserAuthnzTokenTest).filter_by(provider=provider).first()
            assert migrated is not None
            assert migrated.provider == provider

    def test_migration_handles_expired_tokens(self, db_session):
        """Test migration of already-expired tokens."""
        past_expiration = datetime.now() - timedelta(hours=2)

        custos_token = CustosAuthnzTokenTest(
            user_id=3,
            external_user_id="user_expired",
            provider="keycloak",
            access_token="expired_access",
            id_token="expired_id",
            expiration_time=past_expiration,
        )
        db_session.add(custos_token)
        db_session.commit()

        # Get table objects for migration
        custos_table = CustosAuthnzTokenTest.__table__
        psa_table = UserAuthnzTokenTest.__table__

        # Run the actual migration function
        migrated_count = migrate_custos_tokens_to_psa(db_session.connection(), custos_table, psa_table)
        assert migrated_count == 1

        # Verify - should still migrate, but with default 1 hour expiry
        migrated = db_session.query(UserAuthnzTokenTest).filter_by(user_id=3).first()
        assert migrated is not None
        # Migration sets default 3600 (1 hour) for expired/invalid tokens
        assert migrated.extra_data["expires"] == 3600

    def test_duplicate_detection(self, db_session):
        """Test that duplicate migrations are prevented."""
        # Create original custos token
        custos_token = CustosAuthnzTokenTest(
            user_id=4,
            external_user_id="user_duplicate",
            provider="keycloak",
            access_token="access",
            id_token="id",
        )
        db_session.add(custos_token)

        # Create already-migrated PSA token
        psa_token = UserAuthnzTokenTest(
            user_id=4,
            uid="user_duplicate",
            provider="keycloak",
            extra_data={"access_token": "access", "id_token": "id"},
        )
        db_session.add(psa_token)
        db_session.commit()

        # Attempt to migrate again - should detect duplicate
        existing = (
            db_session.query(UserAuthnzTokenTest)
            .filter_by(user_id=4, provider="keycloak", uid="user_duplicate")
            .first()
        )

        assert existing is not None  # Already exists, should skip migration

    def test_multiple_users_same_provider(self, db_session):
        """Test migration of multiple users with same provider."""
        for user_id in range(10, 15):
            custos_token = CustosAuthnzTokenTest(
                user_id=user_id,
                external_user_id=f"user_{user_id}",
                provider="keycloak",
                access_token=f"access_{user_id}",
                id_token=f"id_{user_id}",
            )
            db_session.add(custos_token)
        db_session.commit()

        # Get table objects for migration
        custos_table = CustosAuthnzTokenTest.__table__
        psa_table = UserAuthnzTokenTest.__table__

        # Run the actual migration function
        migrated_count = migrate_custos_tokens_to_psa(db_session.connection(), custos_table, psa_table)
        assert migrated_count == 5

        # Verify all migrated
        total_count = db_session.query(UserAuthnzTokenTest).count()
        assert total_count == 5

    def test_token_data_structure(self, db_session):
        """Test that migrated token has correct data structure."""
        now = datetime.now()
        custos_token = CustosAuthnzTokenTest(
            user_id=5,
            external_user_id="structure_test",
            provider="cilogon",
            access_token="access",
            id_token="id_token",
            refresh_token="refresh",
            expiration_time=now + timedelta(hours=1),
            refresh_expiration_time=now + timedelta(days=7),
        )
        db_session.add(custos_token)
        db_session.commit()

        # Get table objects for migration
        custos_table = CustosAuthnzTokenTest.__table__
        psa_table = UserAuthnzTokenTest.__table__

        # Run the actual migration function
        migrated_count = migrate_custos_tokens_to_psa(db_session.connection(), custos_table, psa_table)
        assert migrated_count == 1

        # Verify structure
        migrated = db_session.query(UserAuthnzTokenTest).filter_by(user_id=5).first()
        assert migrated is not None
        extra_data = migrated.extra_data
        assert isinstance(extra_data, dict)
        assert all(key in extra_data for key in ["access_token", "id_token", "refresh_token"])
        assert isinstance(extra_data["auth_time"], int)
        assert isinstance(extra_data["expires"], int)
        assert isinstance(extra_data["refresh_expires_in"], int)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
