import json
import os
import shutil
import sys
import tempfile
import traceback
from collections.abc import Callable
from typing import (
    Any,
    cast,
    NamedTuple,
)

from galaxy.datatypes.registry import Registry
from galaxy.files import ConfiguredFileSources
from galaxy.job_execution.compute_environment import SharedComputeEnvironment
from galaxy.job_execution.setup import JobIO
from galaxy.managers.dbkeys import GenomeBuilds
from galaxy.metadata.set_metadata import (
    get_metadata_params,
    get_object_store,
    validate_and_load_datatypes_config,
)
from galaxy.model import store
from galaxy.model.store import SessionlessContext
from galaxy.objectstore import BaseObjectStore
from galaxy.structured_app import MinimalToolApp
from galaxy.tools import (
    create_tool_from_representation,
    evaluation,
)
from galaxy.tools.crypt4gh_remote_execution import (
    build_crypt4gh_postrun_command,
    build_crypt4gh_remote_compute_environment,
    collect_declared_crypt4gh_output_targets,
    collect_discovery_crypt4gh_output_specs,
    Crypt4GHRemoteExecutionError,
    should_run_crypt4gh_remote_execution,
)
from galaxy.tools.data import (
    from_dict,
    ToolDataTableManager,
)
from galaxy.util.bunch import Bunch


class ToolAppConfig(NamedTuple):
    name: str
    tool_data_path: str
    galaxy_data_manager_data_path: str
    nginx_upload_path: str
    len_file_path: str
    builds_file_path: str
    root: str
    is_admin_user: Callable
    admin_users: list = []


class Crypt4GHGateConfig(NamedTuple):
    enable_crypt4gh_transparent_input_matching: bool = False
    enable_crypt4gh_remote_execution_staging: bool = False
    enable_crypt4gh_transparent_staging: bool = False
    outputs_to_working_directory: bool = True
    metadata_strategy: str = "extended"
    crypt4gh_reencryption_service_url: str | None = None
    tool_evaluation_strategy: str | None = "remote"


class ToolApp(MinimalToolApp):
    """Dummy App that allows loading tools"""

    name = "tool_app"
    is_webapp = False

    def __init__(
        self,
        sa_session: SessionlessContext,
        tool_app_config: ToolAppConfig,
        datatypes_registry: Registry,
        object_store: BaseObjectStore,
        tool_data_table_manager: ToolDataTableManager,
        file_sources: ConfiguredFileSources,
    ):
        # For backward compatibility we need both context and session attributes that point to sa_session.
        self.model = Bunch(context=sa_session, session=sa_session)
        self.config = tool_app_config
        self.datatypes_registry = datatypes_registry
        self.object_store = object_store
        self.genome_builds = GenomeBuilds(self)
        self._tool_data_tables = tool_data_table_manager
        self.file_sources = file_sources
        self.biotools_metadata_source = None
        self.security = None  # type: ignore[assignment]

    @property
    def tool_data_tables(self) -> ToolDataTableManager:
        return self._tool_data_tables


def main(TMPDIR, WORKING_DIRECTORY, IMPORT_STORE_DIRECTORY) -> None:
    metadata_params = get_metadata_params(WORKING_DIRECTORY)
    datatypes_config = metadata_params["datatypes_config"]
    if not os.path.exists(datatypes_config):
        datatypes_config = os.path.join(WORKING_DIRECTORY, "configs", datatypes_config)
    datatypes_registry = validate_and_load_datatypes_config(datatypes_config)
    object_store = get_object_store(WORKING_DIRECTORY)
    import_store = store.imported_store_for_metadata(IMPORT_STORE_DIRECTORY)
    assert isinstance(import_store.sa_session, SessionlessContext)
    # TODO: clean up random places from which we read files in the working directory
    job_io = JobIO.from_json(os.path.join(IMPORT_STORE_DIRECTORY, "job_io.json"), sa_session=import_store.sa_session)
    tool_app_config = ToolAppConfig(
        name="tool_app",
        tool_data_path=job_io.tool_data_path,
        galaxy_data_manager_data_path=job_io.galaxy_data_manager_data_path,
        nginx_upload_path=TMPDIR,
        len_file_path=job_io.len_file_path,
        builds_file_path=job_io.builds_file_path,
        root=TMPDIR,
        is_admin_user=lambda _: job_io.user_context.is_admin,
    )
    with open(os.path.join(IMPORT_STORE_DIRECTORY, "tool_data_tables.json")) as data_tables_json:
        tdtm = from_dict(json.load(data_tables_json))
    app = ToolApp(
        sa_session=import_store.sa_session,
        tool_app_config=tool_app_config,
        datatypes_registry=datatypes_registry,
        object_store=object_store,
        tool_data_table_manager=tdtm,
        file_sources=job_io.file_sources,
    )
    # TODO: could try to serialize just a minimal tool variant instead of the whole thing ?
    tool = create_tool_from_representation(
        app=app,
        raw_tool_source=job_io.tool_source,
        tool_dir=job_io.tool_dir,
        tool_source_class=job_io.tool_source_class,
    )
    tool_evaluator = evaluation.RemoteToolEvaluator(
        app=app, tool=tool, job=job_io.job, local_working_directory=WORKING_DIRECTORY
    )

    destination_params = dict(job_io.job.destination_params or {})
    crypt4gh_config = cast(dict, job_io.crypt4gh_config or {})
    reencryption_service_url = str(crypt4gh_config.get("reencryption_service_url") or "").strip()
    crypt4gh_gate_config = Crypt4GHGateConfig(
        enable_crypt4gh_transparent_staging=bool(crypt4gh_config.get("enable_crypt4gh_transparent_staging", False)),
        crypt4gh_reencryption_service_url=reencryption_service_url or None,
    )

    crypt4gh_active = False
    crypt4gh_output_targets: list[dict[str, object]] = []
    crypt4gh_discovery_specs: list[dict[str, object]] = []
    crypt4gh_compute_public_key = ""
    crypt4gh_compute_keypair_id = ""
    crypt4gh_compute_keypair_expiration_date = None

    if reencryption_service_url and should_run_crypt4gh_remote_execution(
        job_io=job_io,
        app_config=cast(Any, crypt4gh_gate_config),
        destination_params=destination_params,
        provided_metadata_style=tool.provided_metadata_style,
    ):
        crypt4gh_compute_environment = build_crypt4gh_remote_compute_environment(
            job_io=job_io,
            job=job_io.job,
            working_directory=WORKING_DIRECTORY,
            reencryption_service_url=reencryption_service_url,
        )
        tool_evaluator.set_compute_environment(compute_environment=crypt4gh_compute_environment)
        crypt4gh_active = True
        crypt4gh_compute_public_key = str(crypt4gh_compute_environment.compute_public_key or "")
        crypt4gh_compute_keypair_id = str(crypt4gh_compute_environment.compute_keypair_id or "")
        crypt4gh_compute_keypair_expiration_date = crypt4gh_compute_environment.compute_keypair_expiration_date

        if not crypt4gh_compute_public_key or not crypt4gh_compute_keypair_id:
            raise Crypt4GHRemoteExecutionError(
                "Crypt4GH compute environment did not return compute key context required for output finalization"
            )

        crypt4gh_output_targets = collect_declared_crypt4gh_output_targets(
            job_io=job_io,
            tool_outputs=tool.outputs,
            datatypes_registry=datatypes_registry,
            working_directory=WORKING_DIRECTORY,
        )
        crypt4gh_discovery_specs = collect_discovery_crypt4gh_output_specs(
            job_io=job_io,
            tool_outputs=tool.outputs,
            datatypes_registry=datatypes_registry,
            working_directory=WORKING_DIRECTORY,
        )
    else:
        tool_evaluator.set_compute_environment(compute_environment=SharedComputeEnvironment(job_io=job_io, job=job_io.job))

    with open(os.path.join(WORKING_DIRECTORY, "tool_script.sh"), "a") as out:
        command_line, version_command_line, extra_filenames, environment_variables, *_ = tool_evaluator.build()
        tool_command = f"{version_command_line or ''}{command_line}"
        if crypt4gh_active:
            galaxy_json_path = os.path.join(WORKING_DIRECTORY, "working", "galaxy.json")
            tool_command = build_crypt4gh_postrun_command(
                tool_command=tool_command,
                output_targets=crypt4gh_output_targets,
                discovery_specs=crypt4gh_discovery_specs,
                galaxy_json_path=galaxy_json_path,
                working_directory=WORKING_DIRECTORY,
                reencryption_service_url=reencryption_service_url,
                compute_public_key=crypt4gh_compute_public_key,
                compute_keypair_id=crypt4gh_compute_keypair_id,
                compute_keypair_expiration_date=crypt4gh_compute_keypair_expiration_date,
                python_executable=sys.executable,
            )
        out.write(tool_command)


if __name__ == "__main__":
    TMPDIR = tempfile.mkdtemp()
    WORKING_DIRECTORY = os.getcwd()
    WORKING_PARENT = os.path.join(WORKING_DIRECTORY, os.path.pardir)
    if not os.path.isdir("working") and os.path.isdir(os.path.join(WORKING_PARENT, "working")):
        # We're probably in pulsar
        WORKING_DIRECTORY = WORKING_PARENT
    METADATA_DIRECTORY = os.path.join(WORKING_DIRECTORY, "metadata")
    IMPORT_STORE_DIRECTORY = os.path.join(METADATA_DIRECTORY, "outputs_new")
    EXPORT_STORE_DIRECTORY = os.path.join(METADATA_DIRECTORY, "outputs_populated")
    try:
        main(TMPDIR, WORKING_DIRECTORY, IMPORT_STORE_DIRECTORY)
    except Exception:
        os.makedirs(EXPORT_STORE_DIRECTORY, exist_ok=True)
        with open(os.path.join(EXPORT_STORE_DIRECTORY, "traceback.txt"), "w") as out:
            out.write(traceback.format_exc())
        raise
    finally:
        shutil.rmtree(TMPDIR, ignore_errors=True)
