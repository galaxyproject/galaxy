"""Server-managed authorization for computing on protected (encrypted) datasets.

Protected datasets are stored encrypted. Decrypting them for a job requires a
*grant*: scheme-specific material (for Crypt4GH, the dataset header re-encrypted
to a compute keypair) that a user submits for themselves. Grants are bound to a
``(user, Dataset)`` pair and kept out of dataset metadata, so copying, sharing,
importing or exporting a dataset never transfers the ability to decrypt it.
"""

import base64
import io
import logging
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import (
    Any,
    Protocol,
)

from sqlalchemy import select

from galaxy.config import GalaxyAppConfiguration
from galaxy.datatypes.crypt4gh import Crypt4GH
from galaxy.exceptions import (
    ConfigDoesNotAllowException,
    RequestParameterInvalidException,
)
from galaxy.model import (
    Dataset,
    DatasetInstance,
    DatasetProtectionGrant,
    User,
)
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.schema.dataset_protection import (
    Crypt4GHGrantPayload,
    DatasetProtectionStatus,
)
from galaxy.util import now
from galaxy.util.crypt4gh import read_crypt4gh_header

log = logging.getLogger(__name__)

GRANT_SOURCE_USER = "user"


class GrantRecord:
    def __init__(self, key_ref: str, expires_at: datetime, grant_data: dict[str, Any]):
        self.key_ref = key_ref
        # Stored as naive UTC, like every other Galaxy timestamp.
        self.expires_at = expires_at
        self.grant_data = grant_data


class ProtectionScheme(Protocol):
    name: str
    # Grants closer than this to their expiration can no longer be used by the key service.
    expiry_margin: timedelta

    def handles(self, dataset_instance: DatasetInstance) -> bool: ...

    def validate_user_grant(self, payload: Crypt4GHGrantPayload) -> GrantRecord: ...


class Crypt4GHProtectionScheme:
    name = "crypt4gh"
    # crypt4gh-recryptor-service refuses compute keypairs expiring within a day.
    expiry_margin = timedelta(days=1)
    # The service issues keypairs valid for 7 days, anything far beyond is not a real expiration.
    max_grant_lifetime = timedelta(days=31)

    def handles(self, dataset_instance: DatasetInstance) -> bool:
        return isinstance(dataset_instance.datatype, Crypt4GH)

    def validate_user_grant(self, payload: Crypt4GHGrantPayload) -> GrantRecord:
        try:
            header = base64.b64decode(payload.crypt4gh_compute_header, validate=True)
        except ValueError:
            raise RequestParameterInvalidException("crypt4gh_compute_header is not valid base64.")
        try:
            parsed_header = read_crypt4gh_header(io.BytesIO(header))
        except ValueError as e:
            raise RequestParameterInvalidException(f"crypt4gh_compute_header is not a Crypt4GH header: {e}")
        if parsed_header != header:
            raise RequestParameterInvalidException("crypt4gh_compute_header must contain only the Crypt4GH header.")

        expiration = payload.crypt4gh_compute_keypair_expiration_date
        if expiration.tzinfo is None or expiration.utcoffset() is None:
            raise RequestParameterInvalidException("crypt4gh_compute_keypair_expiration_date must include a timezone.")
        expires_at = expiration.astimezone(timezone.utc).replace(tzinfo=None)
        current_time = now()
        if expires_at <= current_time:
            raise RequestParameterInvalidException("The compute keypair has already expired, recrypt the dataset.")
        if expires_at > current_time + self.max_grant_lifetime:
            raise RequestParameterInvalidException("crypt4gh_compute_keypair_expiration_date is too far in the future.")

        return GrantRecord(
            key_ref=payload.crypt4gh_compute_keypair_id,
            expires_at=expires_at,
            grant_data={"compute_header": payload.crypt4gh_compute_header},
        )


class DatasetProtectionManager:
    def __init__(self, config: GalaxyAppConfiguration, sa_session: galaxy_scoped_session):
        self.sa_session = sa_session
        self.schemes: dict[str, ProtectionScheme] = {}
        if config.crypt4gh_enabled:
            crypt4gh_scheme = Crypt4GHProtectionScheme()
            self.schemes[crypt4gh_scheme.name] = crypt4gh_scheme

    @property
    def enabled(self) -> bool:
        return bool(self.schemes)

    def scheme_for(self, dataset_instance: DatasetInstance) -> ProtectionScheme | None:
        for scheme in self.schemes.values():
            if scheme.handles(dataset_instance):
                return scheme
        return None

    def is_protected(self, dataset_instance: DatasetInstance) -> bool:
        return self.scheme_for(dataset_instance) is not None

    def get_grant(self, user: User, dataset: Dataset, scheme: str) -> DatasetProtectionGrant | None:
        stmt = select(DatasetProtectionGrant).filter_by(user_id=user.id, dataset_id=dataset.id, scheme=scheme)
        return self.sa_session.scalars(stmt).one_or_none()

    def get_usable_grant(self, user: User, dataset_instance: DatasetInstance) -> DatasetProtectionGrant | None:
        """Return the user's grant on this dataset if it can still be used by the key service."""
        scheme = self.scheme_for(dataset_instance)
        dataset = dataset_instance.dataset
        if scheme is None or dataset is None or dataset.purged:
            return None
        grant = self.get_grant(user, dataset, scheme.name)
        if grant is None or grant.is_expired(scheme.expiry_margin):
            return None
        return grant

    def register_user_grant(
        self, user: User, dataset_instance: DatasetInstance, payload: Crypt4GHGrantPayload
    ) -> DatasetProtectionStatus:
        """Store (or replace) the user's grant to compute on an accessible protected dataset.

        Callers are responsible for checking the user can access ``dataset_instance``.
        """
        if not self.enabled:
            raise ConfigDoesNotAllowException("Protected datasets are not enabled on this Galaxy server.")
        scheme = self.scheme_for(dataset_instance)
        if scheme is None or scheme.name != payload.scheme:
            raise RequestParameterInvalidException(f"This dataset is not protected with the '{payload.scheme}' scheme.")
        dataset = dataset_instance.dataset
        if dataset is None or dataset.purged:
            raise RequestParameterInvalidException("Cannot grant access to a purged dataset.")
        record = scheme.validate_user_grant(payload)

        grant = self.get_grant(user, dataset, scheme.name)
        if grant is None:
            grant = DatasetProtectionGrant(user=user, dataset=dataset, scheme=scheme.name)
            self.sa_session.add(grant)
        grant.key_ref = record.key_ref
        grant.expires_at = record.expires_at
        grant.grant_data = record.grant_data
        grant.source = GRANT_SOURCE_USER
        self.sa_session.commit()
        log.info("Registered %s grant for user %s on dataset %s", scheme.name, user.id, dataset.id)
        return self.grant_status(user, dataset_instance)

    def grant_status(self, user: User | None, dataset_instance: DatasetInstance) -> DatasetProtectionStatus:
        scheme = self.scheme_for(dataset_instance)
        if scheme is None:
            return DatasetProtectionStatus(protected=False)
        grant = self.get_usable_grant(user, dataset_instance) if user else None
        return DatasetProtectionStatus(
            protected=True,
            scheme=scheme.name,
            ready=grant is not None,
            expires_at=grant.expires_at if grant else None,
        )
