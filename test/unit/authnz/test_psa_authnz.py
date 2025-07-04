import base64
import secrets
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
)
from io import StringIO
from unittest.mock import (
    MagicMock,
    patch,
)

import jwt
import pytest

# Tools from hazmat should only be used for testing!
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import (
    RSAPrivateKey,
    RSAPublicKey,
)
from jwt import (
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidSignatureError,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from galaxy import model
from galaxy.authnz.managers import AuthnzManager
from galaxy.authnz.psa_authnz import (
    _decode_access_token_helper,
    decode_access_token,
    PSAAuthnz,
)


@pytest.fixture(scope="module")
def engine():
    return create_engine("sqlite:///:memory:")


@pytest.fixture(scope="module")
def db_session(engine):
    model.mapper_registry.metadata.create_all(engine)
    session = Session(bind=engine)
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def mock_oidc_backend_config_file(tmp_path):
    config = """<?xml version="1.0"?>
    <OIDC>
        <provider name="oidc">
            <url>login.example.com</url>
            <client_id>gxyclient</client_id>
            <client_secret>dummyclientsecret</client_secret>
            <redirect_uri>$galaxy_url/authnz/$provider_name/callback</redirect_uri>
            <enable_idp_logout>true</enable_idp_logout>
            <accepted_audiences>gxyclient</accepted_audiences>
        </provider>
    </OIDC>
    """
    filename = tmp_path / "oidc_backends_config.xml"
    filename.write_text(config)
    return filename


@pytest.fixture
def mock_oidc_config_file(tmp_path):
    config = """<?xml version="1.0"?>
    <OIDC>
        <Setter Property="VERIFY_SSL" Value="False" Type="bool"/>
        <Setter Property="REQUESTS_TIMEOUT" Value="3600" Type="float"/>
        <Setter Property="ID_TOKEN_MAX_AGE" Value="3600" Type="float"/>
    </OIDC>
    """
    filename = tmp_path / "oidc_config.xml"
    filename.write_text(config)
    return filename


@dataclass
class AuthTokenData:
    """
    Stores all the information needed to generate an access token and
    test that it can be decoded.
    """

    private_key: RSAPrivateKey
    public_key: RSAPublicKey
    access_token_str: str
    access_token_data: dict
    key_id: str


def create_access_token(
    email: str = "user@example.com",
    roles: list[str] = None,
    iss: str = "https://issuer.example.com",
    sub: str = None,
    iat: int = None,
    exp: int = None,
    aud: str = "https://audience.example.com",
    scope: list[str] = None,
    azp: str = None,
    permissions: list[str] = None,
    algorithm: str = "RS256",
    public_key_id: str = "example-key",
) -> AuthTokenData:
    """
    Create an OIDC access token along with a dummy private and public key
    for signing it. Each field of the payload can be set, but otherwise
    will get a sensible default (e.g. expiry time in the future).
    """
    if roles is None:
        roles = []
    # Generate a random alphanumeric ID
    if sub is None:
        sub = uuid.uuid4().hex
    if iat is None:
        iat = int(datetime.now().strftime("%s"))
    if exp is None:
        exp = int((datetime.now() + timedelta(hours=1)).strftime("%s"))
    if azp is None:
        azp = uuid.uuid4().hex
    if permissions is None:
        permissions = []

    payload = {
        "email": email,
        "biocommons.org.au/roles": roles,
        "iss": iss,
        "sub": sub,
        "aud": [aud],
        "iat": iat,
        "exp": exp,
        "scope": scope,
        "azp": azp,
        "permissions": permissions,
    }
    public_key, private_key = generate_public_private_key_pair()
    access_token_encoded = jwt.encode(
        payload,
        key=private_key,
        algorithm=algorithm,
        headers={"kid": public_key_id},
    )
    return AuthTokenData(
        private_key=private_key,
        public_key=public_key,
        access_token_str=access_token_encoded,
        access_token_data=payload,
        key_id=public_key_id,
    )


def generate_public_private_key_pair():
    # Code from https://fmpm.dev/mocking-auth0-tokens
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return public_key, private_key


def get_jwk_data(public_key: RSAPublicKey):
    """
    Format an RSAPublicKey into the structure PyJWK expects.
    """

    def base64url_uint(val: int) -> str:
        """Base64url encode a big integer."""
        b = val.to_bytes((val.bit_length() + 7) // 8, "big")
        return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")

    numbers = public_key.public_numbers()
    return {"kty": "RSA", "n": base64url_uint(numbers.n), "e": base64url_uint(numbers.e)}


def test_decode_access_token():
    """
    Test we can decode a valid access token.
    """
    # Set up dummy data/mocks
    dummy_access_token = create_access_token()
    mock_social = MagicMock()
    mock_social.extra_data.get.return_value = dummy_access_token.access_token_str
    mock_backend = MagicMock()
    public_key_data = get_jwk_data(dummy_access_token.public_key)
    mock_backend.find_valid_key.return_value = public_key_data
    mock_backend.strategy.config = {"accepted_audiences": dummy_access_token.access_token_data["aud"]}
    mock_backend.id_token_issuer.return_value = dummy_access_token.access_token_data["iss"]
    # Check that access token is decoded successfully to return the original data
    data = decode_access_token(social=mock_social, backend=mock_backend)
    assert data["access_token"] == dummy_access_token.access_token_data


def test_decode_access_token_invalid_key():
    """
    Test that decoding fails when an invalid key is provided.
    """
    # Set up example data and mocks
    dummy_access_token = create_access_token()
    incorrect_public_key, incorrect_private_key = generate_public_private_key_pair()
    mock_social = MagicMock()
    mock_social.extra_data.get.return_value = dummy_access_token.access_token_str
    mock_backend = MagicMock()
    incorrect_public_key_data = get_jwk_data(incorrect_public_key)
    mock_backend.find_valid_key.return_value = incorrect_public_key_data
    mock_backend.strategy.config = {"accepted_audiences": dummy_access_token.access_token_data["aud"]}
    mock_backend.id_token_issuer.return_value = dummy_access_token.access_token_data["iss"]
    # Test that the decode function returns None for the access token
    result = decode_access_token(social=mock_social, backend=mock_backend)
    assert result["access_token"] is None
    # Test the actual decoding raises expected error
    with pytest.raises(InvalidSignatureError):
        _decode_access_token_helper(token_str=dummy_access_token.access_token_str, backend=mock_backend)


def test_decode_access_token_invalid_issuer():
    """
    Test that a token with an invalid issuer (doesn't match what we expect)
    is not decoded/returned
    """
    # Set up example data and mocks
    dummy_access_token = create_access_token(iss="https://invalid.url")
    mock_social = MagicMock()
    mock_social.extra_data.get.return_value = dummy_access_token.access_token_str
    mock_backend = MagicMock()
    public_key_data = get_jwk_data(dummy_access_token.public_key)
    mock_backend.find_valid_key.return_value = public_key_data
    mock_backend.strategy.config = {"accepted_audiences": dummy_access_token.access_token_data["aud"]}
    mock_backend.id_token_issuer.return_value = "https://validissuer.com"
    # Test that the decode function returns None for the access token
    result = decode_access_token(social=mock_social, backend=mock_backend)
    assert result["access_token"] is None
    # Test the actual decoding raises expected error
    with pytest.raises(InvalidIssuerError):
        _decode_access_token_helper(token_str=dummy_access_token.access_token_str, backend=mock_backend)


def test_decode_access_token_invalid_audience():
    """
    Test that a token with an invalid audience (doesn't match what we expect)
    is not decoded/returned
    """
    # Set up example data and mocks
    dummy_access_token = create_access_token(aud="https://invalidaudience.url")
    mock_social = MagicMock()
    mock_social.extra_data.get.return_value = dummy_access_token.access_token_str
    mock_backend = MagicMock()
    public_key_data = get_jwk_data(dummy_access_token.public_key)
    mock_backend.find_valid_key.return_value = public_key_data
    mock_backend.strategy.config = {"accepted_audiences": ["https://validaudience.url"]}
    mock_backend.id_token_issuer.return_value = dummy_access_token.access_token_data["iss"]
    # Test that the decode function returns None for the access token
    result = decode_access_token(social=mock_social, backend=mock_backend)
    assert result["access_token"] is None
    # Test the actual decoding raises expected error
    with pytest.raises(InvalidAudienceError):
        _decode_access_token_helper(token_str=dummy_access_token.access_token_str, backend=mock_backend)


def test_decode_access_token_opaque_token():
    """
    Test that when the access token is opaque (e.g.
    those returned by Google Auth), we don't decode
    and just return None
    """

    def generate_google_style_token():
        prefix = "ya29"
        part1 = secrets.token_urlsafe(32)
        part2 = secrets.token_urlsafe(64)
        return f"{prefix}.{part1}{part2}"

    opaque_token = generate_google_style_token()
    mock_social = MagicMock()
    mock_social.extra_data.get.return_value = opaque_token
    result = decode_access_token(social=mock_social, backend=MagicMock())
    assert result["access_token"] == None


def test_oidc_config_custom_auth_pipeline(mock_oidc_config_file, mock_oidc_backend_config_file):
    custom_auth_pipeline = ("custom", "auth", "steps")
    mock_app = MagicMock()
    mock_app.config.get.side_effect = lambda k, default=None: {"oidc_auth_pipeline": custom_auth_pipeline}.get(k, default)
    mock_app.config.oidc = defaultdict(dict)
    manager = AuthnzManager(
        app=mock_app, oidc_config_file=mock_oidc_config_file, oidc_backends_config_file=mock_oidc_backend_config_file
    )
    psa_authnz = PSAAuthnz(
        provider="oidc", oidc_config=manager.oidc_config, oidc_backend_config=manager.oidc_backends_config,
        app_config=mock_app.config
    )
    assert psa_authnz.config["SOCIAL_AUTH_PIPELINE"] == custom_auth_pipeline


def test_oidc_config_decode_access_token(mock_oidc_config_file, mock_oidc_backend_config_file):
    """
    Test that when we set oidc_decode_access_token in config, the step is added to
    the auth pipeline in PSAAuthnz
    """
    mock_app = MagicMock()
    mock_app.config.get.side_effect = lambda k, default=None: {"oidc_decode_access_token": True}.get(k, default)
    mock_app.config.oidc = defaultdict(dict)
    manager = AuthnzManager(
        app=mock_app, oidc_config_file=mock_oidc_config_file, oidc_backends_config_file=mock_oidc_backend_config_file
    )
    psa_authnz = PSAAuthnz(
        provider="oidc", oidc_config=manager.oidc_config, oidc_backend_config=manager.oidc_backends_config,
        app_config=mock_app.config
    )
    assert "galaxy.authnz.psa_authnz.decode_access_token" in psa_authnz.config["SOCIAL_AUTH_PIPELINE"]


def test_oidc_config_no_decode_access_token(mock_oidc_config_file, mock_oidc_backend_config_file):
    """
    Test that when we set oidc_decode_access_token to false in config (the default),
    the step is not added to the auth pipeline in PSAAuthnz
    """
    mock_app = MagicMock()
    mock_app.config.get.side_effect = lambda k, default=None: {"oidc_decode_access_token": False}.get(k, default)
    mock_app.config.oidc.return_value = defaultdict(dict)
    manager = AuthnzManager(
        app=mock_app, oidc_config_file=mock_oidc_config_file, oidc_backends_config_file=mock_oidc_backend_config_file
    )
    psa_authnz = PSAAuthnz(
        provider="oidc", oidc_config=manager.oidc_config, oidc_backend_config=manager.oidc_backends_config,
        app_config=mock_app.config
    )
    assert "galaxy.authnz.psa_authnz.decode_access_token" not in psa_authnz.config["SOCIAL_AUTH_PIPELINE"]
