"""Server-managed authorization for computing on protected (encrypted) datasets.

Protected datasets are stored encrypted. Decrypting them for a job requires a
*grant*: scheme-specific material (for Crypt4GH, the dataset header re-encrypted
to a compute keypair) that a user submits for themselves. Grants are bound to a
``(user, Dataset)`` pair and kept out of dataset metadata, so copying, sharing,
importing or exporting a dataset never transfers the ability to decrypt it.
"""

import base64
import hashlib
import io
import json
import logging
import os
from collections.abc import Callable
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import (
    Any,
    Protocol,
    TYPE_CHECKING,
)

from pydantic import (
    AwareDatetime,
    TypeAdapter,
    ValidationError,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from galaxy.config import GalaxyAppConfiguration
from galaxy.datatypes.crypt4gh import Crypt4GH
from galaxy.exceptions import (
    ConfigDoesNotAllowException,
    RequestParameterInvalidException,
)
from galaxy.job_execution.protection import (
    protected_directory,
    ProtectedFile,
    ProtectedInput,
    ProtectionDestination,
    ProtectionError,
    ProtectionPlan,
)
from galaxy.job_execution.protection.outputs import (
    CONTENTLESS_OUTCOMES,
    OUTCOME_PROTECTED,
    SIDECAR_FILE,
)
from galaxy.job_execution.protection.stage import (
    CLEANUP_FAILURE_FILE,
    PROTECTION_SETUP_FAILURE_FILE,
)
from galaxy.model import (
    Dataset,
    DatasetInstance,
    DatasetProtectionGrant,
    Job,
    User,
)
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.schema.dataset_protection import (
    Crypt4GHGrantPayload,
    DatasetProtectionStatus,
)
from galaxy.tools.parameters import visit_input_values
from galaxy.tools.parameters.basic import BaseDataToolParameter
from galaxy.util import now
from galaxy.util.crypt4gh import (
    check_crypt4gh,
    is_crypt4gh_file_ext,
    read_crypt4gh_header,
    unwrap_crypt4gh_file_ext,
)

if TYPE_CHECKING:
    from galaxy.job_execution.compute_environment import ComputeEnvironment
    from galaxy.tools import Tool

log = logging.getLogger(__name__)

_AWARE_DATETIME = TypeAdapter(AwareDatetime)

GRANT_SOURCE_USER = "user"
# Tool types that run a plain command line on the compute host. Others (interactive tools,
# data managers, expression tools, ...) would expose decrypted data outside of the job.
PROTECTED_TOOL_TYPES = ("default",)
# Outputs are encrypted after the tool ran, the compute key must outlive the job.
JOB_TTL_MARGIN = timedelta(hours=1)


def _job_outputs(job: Job) -> list[DatasetInstance]:
    """Every dataset a job produced, including discovered datasets and collection elements."""
    # HDAs and LDDAs have separate id sequences.
    outputs: dict[tuple[type, int], DatasetInstance] = {}
    associations: list[Any] = [*job.output_datasets, *job.output_library_datasets]
    for association in associations:
        outputs[(type(association.dataset), association.dataset.id)] = association.dataset
    collections: list[Any] = [
        association.dataset_collection_instance for association in job.output_dataset_collection_instances
    ]
    collections.extend(association.dataset_collection for association in job.output_dataset_collections)
    for collection in collections:
        if collection is not None:
            for dataset_instance in collection.dataset_instances:
                outputs[(type(dataset_instance), dataset_instance.id)] = dataset_instance
    return list(outputs.values())


def _outputs_in_directory(job: Job, compute_environment: "ComputeEnvironment", directory: str) -> bool:
    """Whether the tool writes every declared output of the job inside ``directory``."""
    associations: list[Any] = [*job.output_datasets, *job.output_library_datasets]
    for association in associations:
        # None when a runner doesn't relocate the output: the tool writes to its final location.
        path = compute_environment.output_path_rewrite(association.dataset)
        if not path or not os.path.abspath(path).startswith(os.path.join(os.path.abspath(directory), "")):
            return False
    return True


def _extra_files_expire(grant: DatasetProtectionGrant, margin: timedelta) -> bool:
    """Whether extra files kept from an earlier grant use a compute keypair expiring within ``margin``."""
    extra_files_key = grant.grant_data.get("extra_files_key")
    if not extra_files_key or not grant.grant_data.get("extra_files"):
        return False
    return datetime.fromisoformat(extra_files_key["expires_at"]) <= now() + margin


def _summarize(errors: list[str], limit: int = 3) -> str:
    """Errors for job and dataset info, outputs of large collections may all fail the same way."""
    summary = " ".join(errors[:limit])
    if len(errors) > limit:
        summary += f" ({len(errors) - limit} more errors)"
    return summary


def _read_sidecar(job_directory: str) -> dict[str, Any] | None:
    """Protection results written by the compute host, ``None`` if it wrote none."""
    path = os.path.join(job_directory, SIDECAR_FILE)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        sidecar: dict[str, Any] = json.load(f)
    return sidecar


def _parse_key_expiration(value: str) -> datetime:
    """Expiration date reported by the key service, as naive UTC. Raises ``ValidationError`` without a timezone."""
    # datetime.fromisoformat() only accepts a 'Z' suffix from Python 3.11 on.
    return _AWARE_DATETIME.validate_python(value).astimezone(timezone.utc).replace(tzinfo=None)


def _has_content(dataset_instance: DatasetInstance) -> bool:
    dataset = dataset_instance.dataset
    return bool(dataset and not dataset.purged and dataset.state != Dataset.states.DEFERRED and dataset.file_size)


def _purge(dataset_instance: DatasetInstance) -> None:
    dataset = dataset_instance.dataset
    assert dataset
    dataset_instance.state = Dataset.states.ERROR
    dataset_instance.purged = True
    dataset_instance.deleted = True
    dataset.full_delete()


def _dataset_instances(value: Any) -> list[DatasetInstance]:
    if value is None:
        return []
    if isinstance(value, DatasetInstance):
        return [value]
    if isinstance(value, (list, tuple)):
        return [instance for item in value for instance in _dataset_instances(item)]
    if hasattr(value, "dataset_instances"):
        # Collections, collection elements and collection adapters.
        return list(value.dataset_instances)
    return []


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

    def has_protected_inputs(self, job: Job) -> bool:
        """Whether any input of the job is protected, including collection elements."""
        associations: list[Any] = [*job.input_datasets, *job.input_library_datasets]
        return any(association.dataset and self.is_protected(association.dataset) for association in associations)

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

        try:
            self._store_user_grant(user, dataset, scheme.name, record)
        except IntegrityError:
            # Authorized concurrently (e.g. from another tab), replace the grant that was just stored.
            self.sa_session.rollback()
            self._store_user_grant(user, dataset, scheme.name, record)
        log.info("Registered %s grant for user %s on dataset %s", scheme.name, user.id, dataset.id)
        return self.grant_status(user, dataset_instance)

    def _store_user_grant(self, user: User, dataset: Dataset, scheme: str, record: GrantRecord) -> None:
        grant = self.get_grant(user, dataset, scheme)
        grant_data = dict(record.grant_data)
        if grant is None:
            grant = DatasetProtectionGrant(user=user, dataset=dataset, scheme=scheme)
            self.sa_session.add(grant)
        elif extra_files := (grant.grant_data or {}).get("extra_files"):
            # Users only authorize the primary file again: keep the extra files of protected job outputs,
            # with the compute keypair they are encrypted to, until it expires.
            grant_data["extra_files"] = extra_files
            grant_data["extra_files_key"] = grant.grant_data.get("extra_files_key") or {
                "key_ref": grant.key_ref,
                "expires_at": grant.expires_at.isoformat(),
            }
        grant.key_ref = record.key_ref
        grant.expires_at = record.expires_at
        grant.grant_data = grant_data
        grant.source = GRANT_SOURCE_USER
        self.sa_session.commit()

    def inputs_needing_decryption(self, tool: "Tool", param_values: dict[str, Any]) -> list[DatasetInstance]:
        """Protected datasets the tool reads as their inner datatype, so must be decrypted.

        Inputs of parameters explicitly accepting Crypt4GH formats are passed encrypted.
        """
        return self._protected_inputs(tool, param_values)[0]

    def _protected_inputs(
        self, tool: "Tool", param_values: dict[str, Any]
    ) -> tuple[list[DatasetInstance], list[DatasetInstance]]:
        """The protected inputs to decrypt, and those passed to the tool encrypted."""
        if not self.enabled or (tool.id or "").startswith("__"):
            # Galaxy's internal tools (metadata, export, ...) work with the encrypted data.
            return [], []
        decrypted: dict[int, DatasetInstance] = {}
        encrypted: dict[int, DatasetInstance] = {}

        def visitor(input: Any, value: Any, **kwargs: Any) -> None:
            if not isinstance(input, BaseDataToolParameter):
                return
            accepts_encrypted = any(is_crypt4gh_file_ext(ext) for ext in input.extensions)
            for dataset_instance in _dataset_instances(value):
                dataset = dataset_instance.dataset
                if dataset is None or not self.is_protected(dataset_instance):
                    continue
                if accepts_encrypted:
                    encrypted[dataset.id] = dataset_instance
                else:
                    decrypted[dataset.id] = dataset_instance

        visit_input_values(tool.inputs, param_values, visitor)
        if encrypted.keys() & decrypted.keys():
            raise ProtectionError(
                "The same encrypted dataset can't be used both as an encrypted and as a decrypted input of a job."
            )
        return list(decrypted.values()), list(encrypted.values())

    def check_job_inputs(self, user: User | None, tool: "Tool", param_values: dict[str, Any]) -> None:
        """Early, user-facing version of the :meth:`authorize_job` checks, run when a job is requested.

        Inputs that are not ready yet (e.g. outputs of upstream workflow steps) are checked when the
        job is prepared.
        """
        try:
            to_decrypt = self.inputs_needing_decryption(tool, param_values)
        except ProtectionError as e:
            raise RequestParameterInvalidException(str(e))
        if not to_decrypt:
            return
        if tool.tool_type not in PROTECTED_TOOL_TYPES:
            raise RequestParameterInvalidException(f"Tool '{tool.name}' can't be used with encrypted datasets.")
        for dataset_instance in to_decrypt:
            if dataset_instance.state != DatasetInstance.states.OK:
                continue
            if user is None or self.get_usable_grant(user, dataset_instance) is None:
                raise RequestParameterInvalidException(
                    f"Dataset '{dataset_instance.name}' is encrypted and you are not authorized to decrypt it in jobs. "
                    "Authorize the dataset first (key icon)."
                )

    def authorize_job(
        self,
        job: Job,
        tool: "Tool",
        param_values: dict[str, Any],
        get_destination: Callable[[], ProtectionDestination],
        compute_environment: "ComputeEnvironment",
    ) -> ProtectionPlan | None:
        """Check the job may decrypt its protected inputs and build its protection plan.

        Returns ``None`` for jobs without inputs to decrypt, raises :class:`ProtectionError`
        when the job must not run.
        """
        to_decrypt, passed_encrypted = self._protected_inputs(tool, param_values)
        if not to_decrypt:
            return None
        if tool.tool_type not in PROTECTED_TOOL_TYPES:
            raise ProtectionError(f"Tool '{tool.name}' can't be used with encrypted datasets.")
        job_directory = os.path.dirname(compute_environment.config_directory().rstrip("/"))
        # Only jobs decrypting data depend on their destination.
        destination = get_destination()
        destination.check(outputs_in_job_directory=_outputs_in_directory(job, compute_environment, job_directory))
        assert destination.recryptor
        margin = JOB_TTL_MARGIN + (destination.walltime or timedelta(0))

        inputs_directory = os.path.join(protected_directory(job_directory), "inputs")
        protected_inputs: list[ProtectedInput] = []
        grants: list[DatasetProtectionGrant] = []
        for dataset_instance in to_decrypt:
            scheme = self.scheme_for(dataset_instance)
            assert scheme
            grant = self.get_usable_grant(job.user, dataset_instance) if job.user else None
            if grant is None or grant.is_expired(max(scheme.expiry_margin, margin)):
                raise ProtectionError(
                    f"You are not authorized to decrypt dataset '{dataset_instance.name}', or your authorization "
                    "expires before this job can finish. Authorize the dataset again (key icon) and rerun the job."
                )
            if _extra_files_expire(grant, max(scheme.expiry_margin, margin)):
                raise ProtectionError(
                    f"The extra files of dataset '{dataset_instance.name}' can't be decrypted anymore: their "
                    "authorization comes from the job that created them, and it expires before this job can finish."
                )
            grants.append(grant)
            protected_inputs.append(
                self._protected_input(dataset_instance, grant, compute_environment, inputs_directory)
            )

        return ProtectionPlan(
            scheme="crypt4gh",
            job_directory=job_directory,
            output_key_ref=max(grants, key=lambda grant: grant.expires_at).key_ref,
            recryptor=destination.recryptor,
            inputs=protected_inputs,
            encrypted_inputs=[
                compute_environment.input_path_rewrite(dataset_instance) for dataset_instance in passed_encrypted
            ],
        )

    def _protected_input(
        self,
        dataset_instance: DatasetInstance,
        grant: DatasetProtectionGrant,
        compute_environment: "ComputeEnvironment",
        inputs_directory: str,
    ) -> ProtectedInput:
        dataset = dataset_instance.dataset
        assert dataset
        staged_directory = os.path.join(inputs_directory, str(dataset.id))
        inner_ext = unwrap_crypt4gh_file_ext(dataset_instance.extension) or "dat"
        staged_extra_files_path = os.path.join(staged_directory, "plaintext_files")
        source_extra_files_path = None
        extra_files: dict[str, ProtectedFile] = {}
        extra_files_key = grant.grant_data.get("extra_files_key") or {}
        # Only ask for extra files that exist: Pulsar stages every directory it is asked about.
        if dataset_instance.extra_files_path_exists():
            source_extra_files_path = compute_environment.input_extra_files_rewrite(dataset_instance)
            extra_files = {
                relpath: ProtectedFile(
                    source_path=os.path.join(source_extra_files_path, relpath),
                    staged_path=os.path.join(staged_extra_files_path, relpath),
                    compute_header=compute_header,
                    key_ref=extra_files_key.get("key_ref"),
                )
                for relpath, compute_header in grant.grant_data.get("extra_files", {}).items()
            }
        return ProtectedInput(
            dataset_id=dataset.id,
            key_ref=grant.key_ref,
            primary=ProtectedFile(
                source_path=compute_environment.input_path_rewrite(dataset_instance),
                staged_path=os.path.join(staged_directory, f"plaintext.{inner_ext}"),
                compute_header=grant.grant_data["compute_header"],
            ),
            staged_extra_files_path=staged_extra_files_path,
            source_extra_files_path=source_extra_files_path,
            extra_files=extra_files,
        )

    def setup_failure(self, job_directory: str) -> str | None:
        """Why decrypting the inputs of a protected job failed, if it did: the tool never ran."""
        path = os.path.join(job_directory, PROTECTION_SETUP_FAILURE_FILE)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return f.read().strip() or "Could not decrypt the protected inputs of this job."

    def finish_job(self, job: Job, job_directory: str) -> str | None:
        """Verify every output of a finished protected job was protected, record the grants to reuse them.

        Returns why the job must fail, if it must. Outputs that can't be shown to be encrypted are purged.
        Grants are added to the current session, to be committed together with the job's final state.
        """
        errors: list[str] = []
        cleanup_failure = os.path.join(job_directory, CLEANUP_FAILURE_FILE)
        if os.path.exists(cleanup_failure):
            with open(cleanup_failure) as f:
                errors.append(f.read().strip() or "Could not remove the decrypted data of this job.")

        sidecar = _read_sidecar(job_directory)
        if sidecar is None:
            sidecar = {"datasets": {}}
            errors.append("The outputs of this job could not be verified to be encrypted.")
        errors.extend(sidecar.get("errors", []))
        expires_at: datetime | None = None
        if key_expiration := sidecar.get("key_expiration"):
            try:
                expires_at = _parse_key_expiration(key_expiration)
            except ValidationError:
                errors.append("The key service returned an invalid expiration date for the keys of this job's outputs.")

        protected: list[tuple[DatasetInstance, dict[str, Any]]] = []
        unprotected: list[DatasetInstance] = []
        for dataset_instance in _job_outputs(job):
            assert dataset_instance.dataset
            record = sidecar["datasets"].get(str(dataset_instance.dataset.uuid))
            if record and self._is_verified(dataset_instance, record):
                protected.append((dataset_instance, record))
            elif record and record["outcome"] in CONTENTLESS_OUTCOMES and not _has_content(dataset_instance):
                continue
            else:
                unprotected.append(dataset_instance)

        if unprotected:
            names = ", ".join(f"'{dataset_instance.name}'" for dataset_instance in unprotected)
            errors.append(f"Output(s) {names} could not be verified to be encrypted and were purged.")
            for dataset_instance in unprotected:
                _purge(dataset_instance)
        if errors:
            return _summarize(errors)
        if job.user and expires_at:
            self._record_output_grants(job, sidecar.get("key_ref"), expires_at, protected)
        return None

    def fail_job(self, job: Job, job_directory: str) -> str | None:
        """Remove the data stored for the outputs of a failed protected job, unless it is shown to be encrypted.

        Failed jobs may leave plaintext behind. Their outputs stay in the history, in error state.
        Returns the errors the compute host recorded while protecting the outputs, they explain the failure.
        """
        try:
            sidecar = _read_sidecar(job_directory) or {}
        except Exception:
            log.exception("Could not read the protection results of failed job %s", job.id)
            sidecar = {}
        records = sidecar.get("datasets", {})
        for dataset_instance in _job_outputs(job):
            dataset = dataset_instance.dataset
            assert dataset
            record = records.get(str(dataset.uuid))
            if not dataset.purged and not (record and self._is_verified(dataset_instance, record)):
                dataset.full_delete()
        errors = sidecar.get("errors", [])
        return _summarize(errors) if errors else None

    def _is_verified(self, dataset_instance: DatasetInstance, record: dict[str, Any]) -> bool:
        try:
            return record["outcome"] == OUTCOME_PROTECTED and self._is_protected_as_recorded(dataset_instance, record)
        except Exception:
            log.exception("Could not verify that dataset %s is encrypted", dataset_instance.id)
            return False

    def _is_protected_as_recorded(self, dataset_instance: DatasetInstance, record: dict[str, Any]) -> bool:
        if dataset_instance.extension != record["ext"] or not self.is_protected(dataset_instance):
            return False
        header = dataset_instance.metadata.crypt4gh_header
        if not header or hashlib.sha256(base64.b64decode(header)).hexdigest() != record["header_sha256"]:
            return False
        dataset = dataset_instance.dataset
        assert dataset
        # Data is checked independently of the compute host where it is local (e.g. disk object stores).
        file_name = dataset.get_file_name(sync_cache=False)
        if os.path.exists(file_name):
            with open(file_name, "rb") as f:
                try:
                    stored_header = read_crypt4gh_header(f)
                except ValueError:
                    return False
            if hashlib.sha256(stored_header).hexdigest() != record["header_sha256"]:
                return False
        if dataset.extra_files_path_exists() and os.path.isdir(extra_files_path := dataset.extra_files_path):
            recorded = record.get("extra_files", {})
            for root, _, filenames in os.walk(extra_files_path):
                for filename in filenames:
                    path = os.path.join(root, filename)
                    if os.path.relpath(path, extra_files_path) not in recorded or not check_crypt4gh(path):
                        return False
        return True

    def _record_output_grants(
        self,
        job: Job,
        key_ref: str | None,
        expires_at: datetime,
        protected: list[tuple[DatasetInstance, dict[str, Any]]],
    ) -> None:
        if not protected or not key_ref:
            return
        assert job.user
        for dataset_instance, record in protected:
            if not record["compute_header"]:
                # Encrypted already by the tool, e.g. a copy of an encrypted input.
                continue
            scheme = self.scheme_for(dataset_instance)
            assert scheme and dataset_instance.dataset
            grant = self.get_grant(job.user, dataset_instance.dataset, scheme.name)
            if grant is None:
                grant = DatasetProtectionGrant(user=job.user, dataset=dataset_instance.dataset, scheme=scheme.name)
                self.sa_session.add(grant)
            grant.key_ref = key_ref
            grant.expires_at = expires_at
            extra_files = {relpath: header for relpath, header in record["extra_files"].items() if header}
            grant.grant_data = {"compute_header": record["compute_header"], "extra_files": extra_files}
            grant.source = f"job:{job.id}"

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
