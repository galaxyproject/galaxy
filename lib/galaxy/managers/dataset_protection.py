"""Server-managed authorization for computing on protected (encrypted) datasets.

Protected datasets are stored encrypted. Decrypting them for a job requires a
*grant*: scheme-specific material (for Crypt4GH, the dataset header re-encrypted
to a compute keypair) that a user submits for themselves. Grants are bound to a
``(user, Dataset)`` pair and kept out of dataset metadata, so copying, sharing,
importing or exporting a dataset never transfers the ability to decrypt it.

Crypt4GH is the only protection scheme. Grants record their scheme, so that another
one can be added next to it.
"""

import base64
import hashlib
import io
import logging
import os
from collections.abc import Callable
from datetime import (
    datetime,
    timedelta,
)
from typing import (
    Any,
    TYPE_CHECKING,
)

from pydantic import (
    BaseModel,
    Field,
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
    CRYPT4GH_SCHEME,
    protected_inputs_directory,
    ProtectedFile,
    ProtectedInput,
    ProtectionDestination,
    ProtectionError,
    ProtectionPlan,
)
from galaxy.job_execution.protection.outputs import (
    CONTENTLESS_OUTCOMES,
    ProtectedOutput,
    ProtectionSidecar,
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
    KeyExpirationDate,
)
from galaxy.tool_util_models.tool_source import FileSourceConfigFile
from galaxy.tools.parameters import visit_input_values
from galaxy.tools.parameters.basic import (
    BaseDataToolParameter,
    DataToolParameter,
)
from galaxy.util import now
from galaxy.util.crypt4gh import (
    check_crypt4gh,
    is_crypt4gh_file_ext,
    iter_relpaths,
    read_crypt4gh_header,
    unwrap_crypt4gh_file_ext,
)

if TYPE_CHECKING:
    from galaxy.job_execution.compute_environment import ComputeEnvironment
    from galaxy.tools import Tool

log = logging.getLogger(__name__)

_KEY_EXPIRATION_DATE = TypeAdapter(KeyExpirationDate)

GRANT_SOURCE_USER = "user"
# Tool types that run a plain command line on the compute host. Others (interactive tools,
# data managers, expression tools, ...) would expose decrypted data outside of the job.
PROTECTED_TOOL_TYPES = ("default",)
# Outputs are encrypted after the tool ran, the compute key must outlive the job.
JOB_TTL_MARGIN = timedelta(hours=1)
# Grants closer than this to their expiration can no longer be used by the key service:
# crypt4gh-recryptor-service refuses compute keypairs expiring within a day.
KEY_SERVICE_EXPIRY_MARGIN = timedelta(days=1)
# The key service issues keypairs valid for 7 days, anything far beyond is not a real expiration.
MAX_GRANT_LIFETIME = timedelta(days=31)


class ExtraFilesKey(BaseModel):
    """The compute keypair of extra files kept from the job that created them."""

    key_ref: str
    expires_at: datetime


class Crypt4GHGrantData(BaseModel):
    """The ``grant_data`` of Crypt4GH grants. Headers are bearer capabilities."""

    # Header of the primary file encrypted to the grant's compute keypair. Missing for job outputs
    # copying an encrypted input, until the user authorizes them.
    compute_header: str | None = None
    # Headers of the extra files by relative path, from the job that created the dataset.
    extra_files: dict[str, str] = Field(default_factory=dict)
    # When the extra files are encrypted to another compute keypair than the primary file.
    extra_files_key: ExtraFilesKey | None = None
    # Extra files copying encrypted inputs of the job that created them, they can't be decrypted.
    copied_extra_files: list[str] = Field(default_factory=list)


def _grant_data(grant: DatasetProtectionGrant) -> Crypt4GHGrantData:
    return Crypt4GHGrantData.model_validate(grant.grant_data or {})


def _set_grant_data(grant: DatasetProtectionGrant, grant_data: Crypt4GHGrantData) -> None:
    # Only what was set, the stored data stays as small as it was.
    grant.grant_data = grant_data.model_dump(mode="json", exclude_unset=True)


def _can_decrypt_inputs(tool: "Tool") -> bool:
    if tool.tool_type not in PROTECTED_TOOL_TYPES:
        return False
    # Tools given the user's file sources (e.g. export_remote) would send the decrypted data out of Galaxy.
    return not any(isinstance(config_file, FileSourceConfigFile) for config_file in tool.config_files)


def _shown_name(dataset_instance: DatasetInstance) -> str:
    """The name of the dataset users see, for conversions the one of the dataset they convert."""
    shown = dataset_instance
    for association in getattr(dataset_instance, "implicitly_converted_parent_datasets", []):
        if source := association.parent_hda or association.parent_ldda:
            shown = source
            break
    return shown.name or ""


def _lacks_extra_files(grant: DatasetProtectionGrant) -> bool:
    """Whether the dataset's extra files were protected by another user's job: users only authorize the primary file."""
    if _grant_data(grant).extra_files:
        return False
    return any(
        _grant_data(other).extra_files
        for other in grant.dataset.protection_grants
        if other.scheme == grant.scheme and other.user_id != grant.user_id
    )


def _unsupported_tool_message(tool: "Tool") -> str:
    return f"Tool '{tool.name}' can't be used with encrypted datasets."


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


def _extra_files_expiration(grant: DatasetProtectionGrant) -> datetime | None:
    """Expiration of the compute keypair of extra files kept from an earlier grant, if any."""
    grant_data = _grant_data(grant)
    if not grant_data.extra_files_key or not grant_data.extra_files:
        return None
    return grant_data.extra_files_key.expires_at


def _extra_files_expire(grant: DatasetProtectionGrant, margin: timedelta) -> bool:
    """Whether extra files kept from an earlier grant use a compute keypair expiring within ``margin``."""
    expiration = _extra_files_expiration(grant)
    return expiration is not None and expiration <= now() + margin


_ENCRYPTED_USE_HINT = "It can still be used as-is by tools taking Crypt4GH formats (e.g. c4gh) as input."


def _grant_refusal(grant: DatasetProtectionGrant, dataset_instance: DatasetInstance, margin: timedelta) -> str | None:
    """Why a usable grant still can't decrypt the dataset in a job finishing within ``margin``, if it can't."""
    name = _shown_name(dataset_instance)
    if _grant_data(grant).copied_extra_files:
        return (
            f"The extra files of dataset '{name}' copy encrypted inputs of the job that created them and can't be "
            f"decrypted. {_ENCRYPTED_USE_HINT}"
        )
    if _lacks_extra_files(grant):
        return (
            f"The extra files of dataset '{name}' were encrypted by a job of another user and can only be decrypted "
            f"in their jobs. {_ENCRYPTED_USE_HINT}"
        )
    if _extra_files_expire(grant, margin):
        return (
            f"The extra files of dataset '{name}' can't be decrypted anymore: their authorization comes from the job "
            f"that created them, and it expires before this job can finish. {_ENCRYPTED_USE_HINT}"
        )
    return None


def _needs_grant(record: ProtectedOutput) -> bool:
    """Whether an output has files sealed to the job's compute keypair, or extra files copying encrypted inputs.

    Outputs only copying an encrypted input are used with the grant of the input's copy.
    """
    return bool(record.compute_header or record.extra_files)


def _summarize(errors: list[str], limit: int = 3) -> str:
    """Errors for job and dataset info, outputs of large collections may all fail the same way."""
    summary = " ".join(errors[:limit])
    if len(errors) > limit:
        summary += f" ({len(errors) - limit} more errors)"
    return summary


def _read_report(job_directory: str, relative_path: str, default: str) -> str | None:
    """A failure the compute host reported in a file of the job directory, ``None`` if it reported none."""
    path = os.path.join(job_directory, relative_path)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return f.read().strip() or default


def _parse_key_expiration(value: str) -> datetime:
    """Expiration date reported by the key service, as naive UTC. Raises ``ValidationError`` without a timezone."""
    # datetime.fromisoformat() only accepts a 'Z' suffix from Python 3.11 on.
    return _KEY_EXPIRATION_DATE.validate_python(value)


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


def _existing_conversion(dataset_instance: DatasetInstance, formats: list[Any]) -> DatasetInstance | None:
    """The existing conversion of the dataset to one of ``formats``, as the tool action finds it."""
    direct_match, target_ext, converted_dataset = dataset_instance.find_conversion_destination(formats)
    if not direct_match and target_ext and converted_dataset:
        return converted_dataset
    return None


def _format_ext(format: Any) -> str:
    return format if isinstance(format, str) else format.file_ext


def _read_datasets(
    input: BaseDataToolParameter, dataset_instance: DatasetInstance
) -> list[tuple[DatasetInstance, bool]]:
    """The datasets a tool reads for an input dataset, and whether it reads them encrypted.

    Explicit conversions (``<conversion>``) are passed to the tool next to the input.
    """
    # Implicit conversions replace the input in the job parameters already.
    read = [(dataset_instance, any(is_crypt4gh_file_ext(ext) for ext in input.extensions))]
    if isinstance(input, DataToolParameter):
        for _, conversion_ext, conversion_datatypes in input.conversions:
            if converted_dataset := _existing_conversion(dataset_instance, conversion_datatypes):
                read.append((converted_dataset, is_crypt4gh_file_ext(conversion_ext)))
    return read


class GrantRecord:
    def __init__(self, key_ref: str, expires_at: datetime, grant_data: Crypt4GHGrantData):
        self.key_ref = key_ref
        # Stored as naive UTC, like every other Galaxy timestamp.
        self.expires_at = expires_at
        self.grant_data = grant_data


def validate_crypt4gh_grant(payload: Crypt4GHGrantPayload) -> GrantRecord:
    """Check the compute header returned by the user's key service, and that jobs can use its keypair."""
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

    expires_at = payload.crypt4gh_compute_keypair_expiration_date
    current_time = now()
    if expires_at <= current_time:
        raise RequestParameterInvalidException("The compute keypair has already expired, recrypt the dataset.")
    if expires_at <= current_time + KEY_SERVICE_EXPIRY_MARGIN:
        # The key service would refuse to use it.
        raise RequestParameterInvalidException(
            "The compute keypair expires within a day, jobs can't use it. Authorize the dataset again, and "
            "contact your Galaxy administrator if this keeps happening."
        )
    if expires_at > current_time + MAX_GRANT_LIFETIME:
        raise RequestParameterInvalidException("crypt4gh_compute_keypair_expiration_date is too far in the future.")

    return GrantRecord(
        key_ref=payload.crypt4gh_compute_keypair_id,
        expires_at=expires_at,
        grant_data=Crypt4GHGrantData(compute_header=payload.crypt4gh_compute_header),
    )


class DatasetProtectionManager:
    def __init__(self, config: GalaxyAppConfiguration, sa_session: galaxy_scoped_session):
        self.sa_session = sa_session
        self.enabled = bool(config.crypt4gh_enabled)

    def is_protected(self, dataset_instance: DatasetInstance) -> bool:
        return self.enabled and isinstance(dataset_instance.datatype, Crypt4GH)

    def has_protected_inputs(self, job: Job) -> bool:
        """Whether any input of the job is protected, including collection elements."""
        associations: list[Any] = [*job.input_datasets, *job.input_library_datasets]
        return any(association.dataset and self.is_protected(association.dataset) for association in associations)

    def get_grant(self, user: User, dataset: Dataset) -> DatasetProtectionGrant | None:
        stmt = select(DatasetProtectionGrant).filter_by(user_id=user.id, dataset_id=dataset.id, scheme=CRYPT4GH_SCHEME)
        return self.sa_session.scalars(stmt).one_or_none()

    def _get_or_create_grant(self, user: User, dataset: Dataset) -> DatasetProtectionGrant:
        grant = self.get_grant(user, dataset)
        if grant is None:
            grant = DatasetProtectionGrant(user=user, dataset=dataset, scheme=CRYPT4GH_SCHEME)
            self.sa_session.add(grant)
        return grant

    def get_usable_grant(self, user: User, dataset_instance: DatasetInstance) -> DatasetProtectionGrant | None:
        """Return the user's grant on this dataset if it can still be used by the key service."""
        dataset = dataset_instance.dataset
        if not self.is_protected(dataset_instance) or dataset is None or dataset.purged:
            return None
        grant = self.get_grant(user, dataset)
        if grant is None or grant.is_expired(KEY_SERVICE_EXPIRY_MARGIN) or _grant_data(grant).compute_header is None:
            # Without a compute header, the user still has to authorize the primary file.
            return None
        return grant

    def retire_unusable_conversion(
        self, user: User | None, dataset_instance: DatasetInstance, converted: DatasetInstance, formats: list[Any]
    ) -> bool:
        """Whether the dataset has to be converted again, because the user can't decrypt this conversion.

        Conversions are decrypted with the grants of the jobs that converted them, users can't renew
        those. Every unusable conversion of the dataset is retired then, also those of converter
        dependencies, so they are converted again with the grant of the user on the dataset.
        Users who can't decrypt the dataset either keep the conversions, which may be another user's.
        """
        if user is None or not self.is_protected(converted) or converted.state != DatasetInstance.states.OK:
            return False
        if any(is_crypt4gh_file_ext(_format_ext(format)) for format in formats):
            # Passed to the tool encrypted.
            return False
        if self.get_usable_grant(user, converted) is not None:
            return False
        if self.get_usable_grant(user, dataset_instance) is None:
            # Their job is refused anyway.
            return False
        for association in dataset_instance.implicitly_converted_datasets:
            conversion = association.dataset or association.dataset_ldda
            if (
                not association.deleted
                and conversion is not None
                and conversion.state == DatasetInstance.states.OK
                and self.is_protected(conversion)
                and self.get_usable_grant(user, conversion) is None
            ):
                association.deleted = True
        return True

    def register_user_grant(
        self, user: User, dataset_instance: DatasetInstance, payload: Crypt4GHGrantPayload
    ) -> DatasetProtectionStatus:
        """Store (or replace) the user's grant to compute on an accessible protected dataset.

        Callers are responsible for checking the user can access ``dataset_instance``.
        """
        if not self.enabled:
            raise ConfigDoesNotAllowException("Protected datasets are not enabled on this Galaxy server.")
        if not self.is_protected(dataset_instance):
            raise RequestParameterInvalidException(f"This dataset is not protected with the '{payload.scheme}' scheme.")
        dataset = dataset_instance.dataset
        if dataset is None or dataset.purged:
            raise RequestParameterInvalidException("Cannot grant access to a purged dataset.")
        record = validate_crypt4gh_grant(payload)

        try:
            self._store_user_grant(user, dataset, record)
        except IntegrityError:
            # Authorized concurrently (e.g. from another tab), replace the grant that was just stored.
            self.sa_session.rollback()
            self._store_user_grant(user, dataset, record)
        log.info("Registered grant for user %s on dataset %s", user.id, dataset.id)
        return self.grant_status(user, dataset_instance)

    def _store_user_grant(self, user: User, dataset: Dataset, record: GrantRecord) -> None:
        grant = self._get_or_create_grant(user, dataset)
        previous = _grant_data(grant)
        grant_data = record.grant_data.model_copy()
        if previous.copied_extra_files:
            grant_data.copied_extra_files = previous.copied_extra_files
        if previous.extra_files:
            # Users only authorize the primary file again: keep the extra files of protected job outputs,
            # with the compute keypair they are encrypted to, until it expires.
            grant_data.extra_files = previous.extra_files
            grant_data.extra_files_key = previous.extra_files_key or ExtraFilesKey(
                key_ref=grant.key_ref, expires_at=grant.expires_at
            )
        grant.key_ref = record.key_ref
        grant.expires_at = record.expires_at
        _set_grant_data(grant, grant_data)
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
            for input_instance in _dataset_instances(value):
                for dataset_instance, read_encrypted in _read_datasets(input, input_instance):
                    dataset = dataset_instance.dataset
                    if dataset is None or not self.is_protected(dataset_instance):
                        continue
                    if read_encrypted:
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
        if not _can_decrypt_inputs(tool):
            raise RequestParameterInvalidException(_unsupported_tool_message(tool))
        for dataset_instance in to_decrypt:
            if dataset_instance.state != DatasetInstance.states.OK:
                continue
            grant = self.get_usable_grant(user, dataset_instance) if user else None
            if grant is None:
                raise RequestParameterInvalidException(
                    f"Dataset '{_shown_name(dataset_instance)}' is encrypted and you are not authorized to decrypt it in jobs. "
                    "Authorize the dataset first (key icon)."
                )
            if refusal := _grant_refusal(grant, dataset_instance, KEY_SERVICE_EXPIRY_MARGIN):
                raise RequestParameterInvalidException(refusal)

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
        when the job must not run. Jobs decrypting their inputs are marked protected.
        """
        to_decrypt, passed_encrypted = self._protected_inputs(tool, param_values)
        if not to_decrypt:
            return None
        if not _can_decrypt_inputs(tool):
            raise ProtectionError(_unsupported_tool_message(tool))
        job_directory = os.path.dirname(compute_environment.config_directory().rstrip("/"))
        # Only jobs decrypting data depend on their destination.
        destination = get_destination()
        destination.check(outputs_in_job_directory=_outputs_in_directory(job, compute_environment, job_directory))
        assert destination.recryptor
        # Outputs are encrypted after the job ran, the key service must still accept the keypair then.
        margin = KEY_SERVICE_EXPIRY_MARGIN + JOB_TTL_MARGIN + (destination.walltime or timedelta(0))

        inputs_directory = protected_inputs_directory(job_directory)
        protected_inputs: list[ProtectedInput] = []
        grants: list[DatasetProtectionGrant] = []
        for dataset_instance in to_decrypt:
            grant = self.get_usable_grant(job.user, dataset_instance) if job.user else None
            if grant is None or grant.is_expired(margin):
                raise ProtectionError(
                    f"You are not authorized to decrypt dataset '{_shown_name(dataset_instance)}', or your authorization "
                    "expires before this job can finish. Authorize the dataset again (key icon) and rerun the job."
                )
            if refusal := _grant_refusal(grant, dataset_instance, margin):
                raise ProtectionError(refusal)
            grants.append(grant)
            protected_inputs.append(
                self._protected_input(dataset_instance, grant, compute_environment, inputs_directory)
            )

        job.protection_scheme = CRYPT4GH_SCHEME
        return ProtectionPlan(
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
        grant_data = _grant_data(grant)
        # The extra files of job outputs without a compute header keep the job's compute keypair.
        extra_files_key_ref = grant_data.extra_files_key.key_ref if grant_data.extra_files_key else None
        # Only ask for extra files that exist: Pulsar stages every directory it is asked about.
        if dataset_instance.extra_files_path_exists():
            source_extra_files_path = compute_environment.input_extra_files_rewrite(dataset_instance)
            extra_files = {
                relpath: ProtectedFile(
                    source_path=os.path.join(source_extra_files_path, relpath),
                    staged_path=os.path.join(staged_extra_files_path, relpath),
                    compute_header=compute_header,
                    key_ref=extra_files_key_ref,
                )
                for relpath, compute_header in grant_data.extra_files.items()
            }
        return ProtectedInput(
            dataset_id=dataset.id,
            key_ref=grant.key_ref,
            primary=ProtectedFile(
                source_path=compute_environment.input_path_rewrite(dataset_instance),
                staged_path=os.path.join(staged_directory, f"plaintext.{inner_ext}"),
                compute_header=grant_data.compute_header,
            ),
            staged_extra_files_path=staged_extra_files_path,
            source_extra_files_path=source_extra_files_path,
            extra_files=extra_files,
        )

    def setup_failure(self, job_directory: str) -> str | None:
        """Why decrypting the inputs of a protected job failed, if it did: the tool never ran."""
        return _read_report(
            job_directory, PROTECTION_SETUP_FAILURE_FILE, "Could not decrypt the protected inputs of this job."
        )

    def finish_job(self, job: Job, job_directory: str) -> str | None:
        """Verify every output of a finished protected job was protected, record the grants to reuse them.

        Returns why the job must fail, if it must. Outputs that can't be shown to be encrypted are purged.
        Grants are added to the current session, to be committed together with the job's final state.
        """
        errors: list[str] = []
        if cleanup_failure := _read_report(
            job_directory, CLEANUP_FAILURE_FILE, "Could not remove the decrypted data of this job."
        ):
            errors.append(cleanup_failure)

        sidecar = ProtectionSidecar.read(job_directory)
        if sidecar is None:
            sidecar = ProtectionSidecar()
            errors.append("The outputs of this job could not be verified to be encrypted.")
        errors.extend(sidecar.errors)
        expires_at: datetime | None = None
        if key_expiration := sidecar.key_expiration:
            try:
                expires_at = _parse_key_expiration(key_expiration)
            except ValidationError:
                errors.append("The key service returned an invalid expiration date for the keys of this job's outputs.")

        protected: list[tuple[DatasetInstance, ProtectedOutput]] = []
        unprotected: list[DatasetInstance] = []
        for dataset_instance in _job_outputs(job):
            assert dataset_instance.dataset
            record = sidecar.datasets.get(str(dataset_instance.dataset.uuid))
            if isinstance(record, ProtectedOutput) and self._is_verified(dataset_instance, record):
                protected.append((dataset_instance, record))
            elif record and record.outcome in CONTENTLESS_OUTCOMES and not _has_content(dataset_instance):
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
        needing_grants = [(instance, record) for instance, record in protected if _needs_grant(record)]
        if job.user and needing_grants:
            key_ref = sidecar.key_ref
            if not (expires_at and key_ref):
                # Users couldn't decrypt the outputs in further jobs, without knowing why.
                return "The key service didn't say until when the outputs of this job can be decrypted in further jobs."
            self._record_output_grants(job, key_ref, expires_at, needing_grants)
        return None

    def fail_job(self, job: Job, job_directory: str) -> str | None:
        """Remove the data stored for the outputs of a failed protected job, unless it is shown to be encrypted.

        Failed jobs may leave plaintext behind. Their outputs stay in the history, in error state.
        Returns the errors the compute host recorded while protecting the outputs, they explain the failure.
        """
        try:
            sidecar = ProtectionSidecar.read(job_directory) or ProtectionSidecar()
        except Exception:
            log.exception("Could not read the protection results of failed job %s", job.id)
            sidecar = ProtectionSidecar()
        for dataset_instance in _job_outputs(job):
            dataset = dataset_instance.dataset
            assert dataset
            record = sidecar.datasets.get(str(dataset.uuid))
            if not dataset.purged and not (
                isinstance(record, ProtectedOutput) and self._is_verified(dataset_instance, record)
            ):
                dataset.full_delete()
        return _summarize(sidecar.errors) if sidecar.errors else None

    def _is_verified(self, dataset_instance: DatasetInstance, record: ProtectedOutput) -> bool:
        try:
            return self._is_protected_as_recorded(dataset_instance, record)
        except Exception:
            log.exception("Could not verify that dataset %s is encrypted", dataset_instance.id)
            return False

    def _is_protected_as_recorded(self, dataset_instance: DatasetInstance, record: ProtectedOutput) -> bool:
        if dataset_instance.extension != record.ext or not self.is_protected(dataset_instance):
            return False
        header = dataset_instance.metadata.crypt4gh_header
        if not header or hashlib.sha256(base64.b64decode(header)).hexdigest() != record.header_sha256:
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
            if hashlib.sha256(stored_header).hexdigest() != record.header_sha256:
                return False
        if dataset.extra_files_path_exists() and os.path.isdir(extra_files_path := dataset.extra_files_path):
            for relpath in iter_relpaths(extra_files_path):
                if relpath not in record.extra_files or not check_crypt4gh(os.path.join(extra_files_path, relpath)):
                    return False
        return True

    def _record_output_grants(
        self,
        job: Job,
        key_ref: str,
        expires_at: datetime,
        protected: list[tuple[DatasetInstance, ProtectedOutput]],
    ) -> None:
        assert job.user
        for dataset_instance, record in protected:
            assert dataset_instance.dataset
            grant = self._get_or_create_grant(job.user, dataset_instance.dataset)
            grant.key_ref = key_ref
            grant.expires_at = expires_at
            grant_data = Crypt4GHGrantData(
                extra_files={relpath: header for relpath, header in record.extra_files.items() if header}
            )
            if record.compute_header:
                grant_data.compute_header = record.compute_header
            elif grant_data.extra_files:
                # The primary file copies an encrypted input, the user authorizes it as any other dataset
                # and the extra files keep the job's compute keypair.
                grant_data.extra_files_key = ExtraFilesKey(key_ref=key_ref, expires_at=expires_at)
            if copied := sorted(relpath for relpath, header in record.extra_files.items() if not header):
                # Copies of encrypted inputs, their headers were never sealed to a compute key.
                grant_data.copied_extra_files = copied
            _set_grant_data(grant, grant_data)
            grant.source = f"job:{job.id}"

    def grant_status(self, user: User | None, dataset_instance: DatasetInstance) -> DatasetProtectionStatus:
        if not self.is_protected(dataset_instance):
            return DatasetProtectionStatus(protected=False)
        grant = self.get_usable_grant(user, dataset_instance) if user else None
        usable_until = None
        if grant:
            # Authorizing the dataset again doesn't renew the keypair of extra files kept from its job.
            expirations = [grant.expires_at, _extra_files_expiration(grant)]
            # The key service refuses keypairs close to their expiration already.
            usable_until = min(e for e in expirations if e is not None) - KEY_SERVICE_EXPIRY_MARGIN
        return DatasetProtectionStatus(
            protected=True,
            scheme=CRYPT4GH_SCHEME,
            ready=grant is not None,
            expires_at=usable_until,
        )
