"""
Tests for the custos-to-PSA database migration.

This test suite verifies the migration script that moves authentication tokens
from custos_authnz_token to oidc_user_authnz_tokens.
"""

import jwt
from datetime import (
    datetime,
    timedelta,
)
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

from galaxy.model.custom_types import MutableJSONType
from galaxy.model.migrations.data_fixes.custos_to_psa import (
    CUSTOS_ASSOC_TYPE,
    _extract_iat_from_token,
    migrate_custos_tokens_to_psa,
    remove_migrated_psa_tokens,
    restore_custos_tokens_from_psa,
)

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
        assert migrated.assoc_type == CUSTOS_ASSOC_TYPE
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
        assert migrated.assoc_type == CUSTOS_ASSOC_TYPE
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
            assert migrated.assoc_type == CUSTOS_ASSOC_TYPE

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

        # Verify - should still migrate, but with expires=1 to trigger refresh
        migrated = db_session.query(UserAuthnzTokenTest).filter_by(user_id=3).first()
        assert migrated is not None
        assert migrated.assoc_type == CUSTOS_ASSOC_TYPE
        # Migration sets expires=1 for expired tokens to trigger immediate refresh
        assert migrated.extra_data["expires"] == 1

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
        assert all(token.assoc_type == CUSTOS_ASSOC_TYPE for token in db_session.query(UserAuthnzTokenTest))

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
        assert migrated.assoc_type == CUSTOS_ASSOC_TYPE
        extra_data = migrated.extra_data
        assert isinstance(extra_data, dict)
        assert all(key in extra_data for key in ["access_token", "id_token", "refresh_token"])
        assert isinstance(extra_data["auth_time"], int)
        assert isinstance(extra_data["expires"], int)
        assert isinstance(extra_data["refresh_expires_in"], int)

    def test_restore_and_remove(self, db_session):
        """Test restoring Custos tokens from PSA and removing migrated records."""
        now = datetime.now()
        expiration = now + timedelta(hours=2)
        refresh_expiration = now + timedelta(days=1)

        custos_token = CustosAuthnzTokenTest(
            user_id=42,
            external_user_id="restore_me",
            provider="custos",
            access_token="access",
            id_token="id_token",
            refresh_token="refresh",
            expiration_time=expiration,
            refresh_expiration_time=refresh_expiration,
        )
        db_session.add(custos_token)
        db_session.commit()

        custos_table = CustosAuthnzTokenTest.__table__
        psa_table = UserAuthnzTokenTest.__table__

        migrated_count = migrate_custos_tokens_to_psa(db_session.connection(), custos_table, psa_table)
        assert migrated_count == 1

        # Simulate drop by clearing Custos table contents
        db_session.query(CustosAuthnzTokenTest).delete()
        db_session.commit()

        restored = restore_custos_tokens_from_psa(db_session.connection(), custos_table, psa_table)
        assert restored == 1

        restored_row = db_session.query(CustosAuthnzTokenTest).filter_by(user_id=42).first()
        assert restored_row is not None
        assert restored_row.access_token == "access"
        assert restored_row.refresh_token == "refresh"
        assert restored_row.expiration_time is not None

        removed = remove_migrated_psa_tokens(db_session.connection(), custos_table, psa_table)
        assert removed == 1

        remaining = db_session.query(UserAuthnzTokenTest).filter_by(user_id=42).first()
        assert remaining is None


class TestExtractIatFromToken:
    """Test the _extract_iat_from_token helper function."""

    def test_extract_iat_from_valid_jwt(self):
        """Test extracting iat from a valid JWT token."""
        iat_value = 1234567890
        token = jwt.encode({"iat": iat_value, "sub": "user123"}, "secret", algorithm="HS256")
        result = _extract_iat_from_token(token)
        assert result == iat_value

    def test_extract_iat_from_jwt_without_iat(self):
        """Test extracting iat from a JWT that doesn't have an iat claim."""
        token = jwt.encode({"sub": "user123", "exp": 9999999999}, "secret", algorithm="HS256")
        result = _extract_iat_from_token(token)
        assert result is None

    def test_extract_iat_from_opaque_token(self):
        """Test extracting iat from an opaque (non-JWT) token."""
        opaque_token = "this_is_not_a_jwt_token"
        result = _extract_iat_from_token(opaque_token)
        assert result is None

    def test_extract_iat_from_none(self):
        """Test extracting iat when token is None."""
        result = _extract_iat_from_token(None)
        assert result is None

    def test_extract_iat_from_empty_string(self):
        """Test extracting iat when token is empty string."""
        result = _extract_iat_from_token("")
        assert result is None

    def test_extract_iat_from_malformed_jwt(self):
        """Test extracting iat from a malformed JWT."""
        malformed_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"
        result = _extract_iat_from_token(malformed_token)
        assert result is None


class TestAuthTimeExtraction:
    """Test auth_time extraction from tokens during migration."""

    def test_auth_time_from_access_token(self, db_session):
        """Test that auth_time is extracted from access_token.iat when available."""
        now = datetime.now()
        access_iat = int(now.timestamp()) - 100  # 100 seconds ago
        id_iat = int(now.timestamp()) - 200  # 200 seconds ago

        access_token = jwt.encode({"iat": access_iat, "sub": "user"}, "secret", algorithm="HS256")
        id_token = jwt.encode({"iat": id_iat, "sub": "user"}, "secret", algorithm="HS256")

        custos_token = CustosAuthnzTokenTest(
            user_id=100,
            external_user_id="user_auth_time_test",
            provider="keycloak",
            access_token=access_token,
            id_token=id_token,
            expiration_time=now + timedelta(hours=1),
        )
        db_session.add(custos_token)
        db_session.commit()

        custos_table = CustosAuthnzTokenTest.__table__
        psa_table = UserAuthnzTokenTest.__table__

        migrated_count = migrate_custos_tokens_to_psa(db_session.connection(), custos_table, psa_table)
        assert migrated_count == 1

        migrated = db_session.query(UserAuthnzTokenTest).filter_by(user_id=100).first()
        assert migrated is not None
        # Should use access_token.iat, not id_token.iat
        assert migrated.extra_data["auth_time"] == access_iat

    def test_auth_time_fallback_to_id_token(self, db_session):
        """Test that auth_time falls back to id_token.iat when access_token is opaque."""
        now = datetime.now()
        id_iat = int(now.timestamp()) - 150

        id_token = jwt.encode({"iat": id_iat, "sub": "user"}, "secret", algorithm="HS256")

        custos_token = CustosAuthnzTokenTest(
            user_id=101,
            external_user_id="user_fallback_test",
            provider="keycloak",
            access_token="opaque_access_token",  # Not a JWT
            id_token=id_token,
            expiration_time=now + timedelta(hours=1),
        )
        db_session.add(custos_token)
        db_session.commit()

        custos_table = CustosAuthnzTokenTest.__table__
        psa_table = UserAuthnzTokenTest.__table__

        migrated_count = migrate_custos_tokens_to_psa(db_session.connection(), custos_table, psa_table)
        assert migrated_count == 1

        migrated = db_session.query(UserAuthnzTokenTest).filter_by(user_id=101).first()
        assert migrated is not None
        # Should use id_token.iat since access_token is opaque
        assert migrated.extra_data["auth_time"] == id_iat

    def test_auth_time_fallback_to_migration_time(self, db_session):
        """Test that auth_time falls back to migration time when both tokens are opaque."""
        now = datetime.now()
        migration_start = int(now.timestamp())

        custos_token = CustosAuthnzTokenTest(
            user_id=102,
            external_user_id="user_no_jwt_test",
            provider="keycloak",
            access_token="opaque_access",
            id_token="opaque_id",
            expiration_time=now + timedelta(hours=1),
        )
        db_session.add(custos_token)
        db_session.commit()

        custos_table = CustosAuthnzTokenTest.__table__
        psa_table = UserAuthnzTokenTest.__table__

        migrated_count = migrate_custos_tokens_to_psa(db_session.connection(), custos_table, psa_table)
        assert migrated_count == 1

        migrated = db_session.query(UserAuthnzTokenTest).filter_by(user_id=102).first()
        assert migrated is not None
        # Should use migration time (approximately)
        auth_time = migrated.extra_data["auth_time"]
        # Allow 5 second window for migration execution
        assert migration_start - 5 <= auth_time <= int(datetime.now().timestamp())

    def test_expires_calculation_with_valid_expiration(self, db_session):
        """Test that expires is calculated correctly from expiration_time and auth_time."""
        now = datetime.now()
        access_iat = int(now.timestamp())
        expiration_time = now + timedelta(hours=2)  # 2 hours = 7200 seconds

        access_token = jwt.encode({"iat": access_iat, "sub": "user"}, "secret", algorithm="HS256")

        custos_token = CustosAuthnzTokenTest(
            user_id=103,
            external_user_id="user_expires_test",
            provider="keycloak",
            access_token=access_token,
            id_token="id_token",
            expiration_time=expiration_time,
        )
        db_session.add(custos_token)
        db_session.commit()

        custos_table = CustosAuthnzTokenTest.__table__
        psa_table = UserAuthnzTokenTest.__table__

        migrated_count = migrate_custos_tokens_to_psa(db_session.connection(), custos_table, psa_table)
        assert migrated_count == 1

        migrated = db_session.query(UserAuthnzTokenTest).filter_by(user_id=103).first()
        assert migrated is not None
        # expires = expiration_time - auth_time
        # Should be approximately 7200 seconds (2 hours)
        expires = migrated.extra_data["expires"]
        assert 7195 <= expires <= 7205  # Allow small timing variance

    def test_expires_set_to_one_for_expired_tokens(self, db_session):
        """Test that expires is set to 1 for already-expired tokens."""
        now = datetime.now()
        # Token issued 2 hours ago, expired 1 hour ago (1 hour lifetime)
        access_iat = int((now - timedelta(hours=2)).timestamp())
        expiration_time = now - timedelta(hours=1)  # Expired 1 hour ago

        access_token = jwt.encode({"iat": access_iat, "sub": "user"}, "secret", algorithm="HS256")

        custos_token = CustosAuthnzTokenTest(
            user_id=104,
            external_user_id="user_expired_test",
            provider="keycloak",
            access_token=access_token,
            id_token="id_token",
            expiration_time=expiration_time,
        )
        db_session.add(custos_token)
        db_session.commit()

        custos_table = CustosAuthnzTokenTest.__table__
        psa_table = UserAuthnzTokenTest.__table__

        migrated_count = migrate_custos_tokens_to_psa(db_session.connection(), custos_table, psa_table)
        assert migrated_count == 1

        migrated = db_session.query(UserAuthnzTokenTest).filter_by(user_id=104).first()
        assert migrated is not None
        # Expired tokens should have expires = 1 to trigger immediate refresh
        # Note: expires = expiration_time - auth_time, and if already expired (expires < 0), set to 1
        assert migrated.extra_data["expires"] == 1

    def test_expires_set_to_one_when_expiration_missing(self, db_session):
        """Test that expires is set to 1 when expiration_time is missing."""
        custos_token = CustosAuthnzTokenTest(
            user_id=105,
            external_user_id="user_no_expiration",
            provider="keycloak",
            access_token="access_token",
            id_token="id_token",
            expiration_time=None,  # No expiration time
        )
        db_session.add(custos_token)
        db_session.commit()

        custos_table = CustosAuthnzTokenTest.__table__
        psa_table = UserAuthnzTokenTest.__table__

        migrated_count = migrate_custos_tokens_to_psa(db_session.connection(), custos_table, psa_table)
        assert migrated_count == 1

        migrated = db_session.query(UserAuthnzTokenTest).filter_by(user_id=105).first()
        assert migrated is not None
        # Missing expiration should result in expires = 1 to trigger refresh
        assert migrated.extra_data["expires"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
