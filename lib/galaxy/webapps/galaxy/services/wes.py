"""GA4GH WES (Workflow Execution Service) implementation for Galaxy."""

import json
import logging
from dataclasses import dataclass
from typing import (
    Any,
    Optional,
)
from urllib.parse import (
    parse_qs,
    urlparse,
)

import yaml
from fastapi import UploadFile
from sqlalchemy import (
    literal,
    select,
    tuple_,
    union_all,
)
from sqlalchemy.orm import joinedload

from galaxy import exceptions
from galaxy.config import GalaxyAppConfiguration
from galaxy.files.uris import stream_url_to_str
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.workflows import (
    RawWorkflowDescription,
    WorkflowContentsManager,
    WorkflowCreateOptions,
)
from galaxy.model import (
    History,
    ImplicitCollectionJobs,
    ImplicitCollectionJobsJobAssociation,
    Job,
    WorkflowInvocation,
    WorkflowInvocationStep,
)
from galaxy.model.keyset_token_pagination import (
    KeysetPagination,
    SingleKeysetToken,
)
from galaxy.schema.wes import (
    DefaultWorkflowEngineParameter,
    RunId,
    RunListResponse,
    RunLog,
    RunRequest,
    RunStatus,
    RunSummary,
    ServiceInfo,
    State,
    TaskListResponse,
    TaskLog,
    WorkflowEngineVersion,
    WorkflowTypeVersion,
)
from galaxy.schema.workflows import InvokeWorkflowPayload
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.webapps.galaxy.services.base import ServiceBase
from galaxy.webapps.galaxy.services.ga4gh import build_service_info
from galaxy.webapps.galaxy.services.workflows import WorkflowsService
from galaxy.work.context import SessionRequestContext

log = logging.getLogger(__name__)

# Map Galaxy workflow invocation states to WES states
GALAXY_TO_WES_STATE = {
    "new": State.QUEUED,
    "ready": State.INITIALIZING,
    "scheduled": State.RUNNING,
    "failed": State.EXECUTOR_ERROR,
    "cancelled": State.CANCELED,
    "cancelling": State.CANCELING,
}

WES_TO_GALAXY_STATE = {v: k for k, v in GALAXY_TO_WES_STATE.items()}


@dataclass
class TaskKeysetToken:
    """Composite keyset token for task pagination (step_order, job_index).

    Used to identify position in task list for cursor-based pagination.
    """

    step_order: int
    job_index: int

    def to_values(self) -> list:
        """Convert token to normalized list of values for encoding."""
        return [self.step_order, self.job_index]

    @classmethod
    def from_values(cls, values: list) -> "TaskKeysetToken":
        """Reconstruct token from decoded values."""
        if len(values) < 2:
            raise ValueError("TaskKeysetToken requires at least 2 values")
        return cls(step_order=values[0], job_index=values[1])


def _parse_gxworkflow_uri(workflow_url: str) -> tuple[str, bool]:
    """Parse a gxworkflow:// URI to extract workflow ID and instance flag.

    Format: gxworkflow://<encoded_workflow_id>[?instance=<false|true>]
    - encoded_workflow_id: Encoded Galaxy workflow ID
    - instance: Optional parameter (defaults to False)
      - False: Load the StoredWorkflow (workflow definition)
      - True: Load the Workflow (active workflow instance)

    Args:
        workflow_url: The gxworkflow:// URI

    Returns:
        Tuple of (encoded_workflow_id, instance_flag)

    Raises:
        exceptions.MessageException: If URI format is invalid
    """
    try:
        parsed = urlparse(workflow_url)

        # Verify scheme is gxworkflow
        if parsed.scheme != "gxworkflow":
            raise ValueError("Invalid scheme, must be gxworkflow://")

        # Extract workflow ID (netloc + path)
        workflow_id = parsed.netloc + parsed.path if parsed.path else parsed.netloc

        if not workflow_id:
            raise ValueError("Missing workflow ID in gxworkflow:// URI")

        # Parse query parameters for instance flag
        instance = False
        if parsed.query:
            params = parse_qs(parsed.query)
            if "instance" in params:
                instance_str = params["instance"][0].lower()
                if instance_str not in ("true", "false"):
                    raise ValueError("instance parameter must be 'true' or 'false'")
                instance = instance_str == "true"

        return workflow_id, instance

    except ValueError as e:
        raise exceptions.MessageException(f"Invalid gxworkflow:// URI: {str(e)}")
    except Exception as e:
        raise exceptions.MessageException(f"Error parsing gxworkflow:// URI: {str(e)}")


def _load_workflow_content(
    trans: ProvidesUserContext,
    workflow_attachment: Optional[UploadFile],
    workflow_url: Optional[str],
) -> dict[str, Any]:
    """Load workflow content from attachment or URL.

    Handles three input methods:
    1. workflow_attachment: Uploaded file
    2. workflow_url with gxworkflow:// scheme: Load from Galaxy database
    3. workflow_url with other schemes: Fetch from URL (http, base64, etc.)

    Returns the workflow as a dictionary for normalization.

    Args:
        trans: Galaxy transaction/context
        workflow_attachment: Uploaded workflow file
        workflow_url: URL to fetch workflow from

    Returns:
        Dictionary representation of the workflow

    Raises:
        exceptions.MessageException: If workflow cannot be loaded
    """
    workflow_content = None

    # Load from attachment file
    if workflow_attachment:
        try:
            # Read the uploaded file content
            content = workflow_attachment.file.read()
            workflow_content = content.decode("utf-8")
        except UnicodeDecodeError:
            raise exceptions.MessageException("Workflow attachment must be UTF-8 encoded text")
        except Exception as e:
            raise exceptions.MessageException(f"Error reading workflow attachment: {str(e)}")

    # Load from URL
    elif workflow_url:
        # Handle gxworkflow:// scheme (Galaxy database reference)
        if workflow_url.startswith("gxworkflow://"):
            # This will be handled by the WesService that has access to workflows_manager
            # Return a special marker dict that includes the URI for later processing
            return {"workflow_uri": workflow_url}

        # Handle other URL schemes (http, https, base64, file, etc.)
        try:
            # Fetch workflow content from URL
            # validate_non_local is called via HTTPFilesSource for security
            workflow_content = stream_url_to_str(workflow_url, trans.app.file_sources)
        except exceptions.AuthenticationRequired as e:
            raise e
        except Exception as e:
            raise exceptions.MessageException(f"Error fetching workflow from URL: {str(e)}")

    if workflow_content is None:
        raise exceptions.RequestParameterMissingException("Either workflow_url or workflow_attachment must be provided")

    assert isinstance(workflow_content, str)

    # Parse as JSON or YAML
    try:
        return json.loads(workflow_content)
    except json.JSONDecodeError:
        # Try as YAML-like dict string - Galaxy's normalize_workflow_format
        # will handle YAML parsing
        return {"yaml_content": workflow_content}


def _determine_workflow_type(workflow_dict: dict[str, Any]) -> str:
    """Determine Galaxy workflow type from workflow dictionary.

    For WES, we support:
    - gx_workflow_ga: Native Galaxy workflow format
    - gx_workflow_format2: Format2 (CWL-style) Galaxy workflows

    Args:
        workflow_dict: The parsed workflow dictionary

    Returns:
        The Galaxy workflow type identifier

    Raises:
        exceptions.MessageException: If workflow type cannot be determined
    """
    # Check for Format2 indicators - either already parsed or in yaml_content
    check_dict = workflow_dict
    if "yaml_content" in workflow_dict:
        try:
            check_dict = yaml.safe_load(workflow_dict["yaml_content"])
        except yaml.YAMLError:
            # If YAML parsing fails, assume Format2 (will fail later with better error)
            return "gx_workflow_format2"

    if check_dict.get("class") == "GalaxyWorkflow":
        return "gx_workflow_format2"

    # Check for native Galaxy workflow format
    if "steps" in check_dict or "workflow" in check_dict:
        return "gx_workflow_ga"

    raise exceptions.MessageException(
        "Cannot determine workflow type from RunRequest. Supported types: gx_workflow_ga, gx_workflow_format2"
    )


def _normalize_run_request(
    trans: ProvidesUserContext,
    workflow_contents_manager: WorkflowContentsManager,
    workflow_dict: dict[str, Any],
) -> RawWorkflowDescription:
    """Normalize workflow content for Galaxy consumption.

    Converts WES workflow format to Galaxy's internal format.

    Args:
        trans: Galaxy transaction/context
        workflow_contents_manager: Galaxy workflow contents manager
        workflow_dict: The parsed workflow dictionary

    Returns:
        RawWorkflowDescription ready for workflow creation

    Raises:
        exceptions.MessageException: If normalization fails
    """
    return workflow_contents_manager.normalize_workflow_format(trans, workflow_dict)


def _get_or_create_history(
    trans: ProvidesUserContext,
    engine_params: dict[str, Any],
) -> History:
    """Get or create a history for the WES run.

    If history_id is provided in engine_params, use existing history.
    Otherwise, create new history with name from history_name or auto-generated.

    Args:
        trans: Galaxy transaction/context
        engine_params: Workflow engine parameters from RunRequest

    Returns:
        History object for the workflow invocation

    Raises:
        exceptions.ObjectNotFound: If specified history_id does not exist
        exceptions.AuthenticationRequired: If user cannot access history
    """
    # Check if specific history requested
    if "history_id" in engine_params:
        history_id = engine_params["history_id"]
        # Decode the ID if it's encoded
        try:
            decoded_id = trans.security.decode_id(history_id)
        except Exception:
            # If decode fails, assume it's already decoded
            decoded_id = history_id

        history = trans.sa_session.query(History).filter_by(id=decoded_id, user_id=trans.user.id).one_or_none()
        if not history:
            raise exceptions.ObjectNotFound(f"History {history_id} not found or not accessible")
        return history

    # Create new history
    history = History(user=trans.user, name=_generate_history_name(engine_params))
    trans.sa_session.add(history)
    trans.sa_session.flush()
    # Postgres tests in CI fail without this commit.
    trans.sa_session.commit()
    return history


def _generate_history_name(engine_params: dict[str, Any]) -> str:
    """Generate a name for auto-created history.

    Uses history_name from engine_params if provided, otherwise generates one.

    Args:
        engine_params: Workflow engine parameters

    Returns:
        History name string
    """
    if "history_name" in engine_params and engine_params["history_name"]:
        return engine_params["history_name"]

    return "WES Run"


class WesService(ServiceBase):
    """Service for handling GA4GH WES API requests."""

    _security: IdEncodingHelper

    def __init__(
        self,
        workflows_service: WorkflowsService,
        config: GalaxyAppConfiguration,
        security: IdEncodingHelper,
    ):
        self._workflows_service = workflows_service
        self._config = config
        self._security = security
        self._keyset_pagination = KeysetPagination()

    def service_info(self, trans: ProvidesUserContext, request_url: str) -> ServiceInfo:
        """Return WES service information.

        Args:
            trans: Galaxy transaction/context
            request_url: The request URL used to build service endpoint URLs

        Returns:
            ServiceInfo object with Galaxy WES capabilities
        """
        # Build base service info using shared utility
        base_service = build_service_info(
            config=self._config,
            request_url=request_url,
            artifact="wes",
            service_name="Galaxy WES API",
            service_description="Executes Galaxy workflows according to the GA4GH WES specification",
            artifact_version="1.0.0",
        )
        # TODO:
        auth_instructions_url = "TODO"

        # Import Organization and ServiceType from WES schema
        from galaxy.schema.wes import (
            Organization as WESOrganization,
            ServiceType as WESServiceType,
        )

        # Convert DRS Service objects to WES schema objects
        organization = WESOrganization(
            name=base_service.organization.name,
            url=base_service.organization.url,
        )
        service_type = WESServiceType(
            group=base_service.type.group,
            artifact=base_service.type.artifact,
            version=base_service.type.version,
        )

        # Create ServiceInfo with WES-specific fields
        return ServiceInfo(
            id=base_service.id,
            name=base_service.name,
            type=service_type,
            description=base_service.description,
            organization=organization,
            contactUrl=base_service.contactUrl,
            documentationUrl=base_service.documentationUrl,
            createdAt=base_service.createdAt,
            updatedAt=base_service.updatedAt,
            environment=base_service.environment,
            version=base_service.version,
            workflow_type_versions={
                "gx_workflow_ga": WorkflowTypeVersion(workflow_type_version=["1.0.0"]),
                "gx_workflow_format2": WorkflowTypeVersion(workflow_type_version=["1.0.0"]),
            },
            supported_wes_versions=["1.0.0"],
            supported_filesystem_protocols=["http", "https", "file", "s3", "gs"],
            workflow_engine_versions={
                "galaxy": WorkflowEngineVersion(workflow_engine_version=["1.0.0"]),
            },
            default_workflow_engine_parameters=[
                DefaultWorkflowEngineParameter(
                    name="history_name",
                    type="string",
                    default_value="",
                ),
                DefaultWorkflowEngineParameter(
                    name="history_id",
                    type="string",
                    default_value="",
                ),
                DefaultWorkflowEngineParameter(
                    name="preferred_object_store_id",
                    type="string",
                    default_value="",
                ),
                DefaultWorkflowEngineParameter(
                    name="use_cached_job",
                    type="boolean",
                    default_value="false",
                ),
            ],
            system_state_counts=dict.fromkeys([s.value for s in State], 0),
            auth_instructions_url=auth_instructions_url,
            tags={},
        )

    def submit_run(
        self,
        trans: ProvidesUserContext,
        workflow_params: Optional[str] = None,
        workflow_type: Optional[str] = None,
        workflow_type_version: Optional[str] = None,
        workflow_url: Optional[str] = None,
        workflow_engine_parameters: Optional[str] = None,
        workflow_engine: Optional[str] = None,
        workflow_engine_version: Optional[str] = None,
        tags: Optional[str] = None,
        workflow_attachment: Optional[UploadFile] = None,
    ) -> RunId:
        """Submit a new workflow run.

        Args:
            trans: Galaxy transaction/context
            workflow_params: JSON string of workflow parameters
            workflow_type: Type of workflow (gx_workflow_ga, gx_workflow_format2)
            workflow_type_version: Version of the workflow type
            workflow_url: URL to fetch workflow from
            workflow_engine_parameters: JSON string of engine parameters
            workflow_engine: Workflow engine name
            workflow_engine_version: Version of workflow engine
            tags: JSON string of tags
            workflow_attachment: Uploaded workflow file

        Returns:
            RunId containing the created run ID
        """
        if trans.anonymous:
            raise exceptions.AuthenticationRequired("You need to be logged in to submit workflows.")

        trans.check_user_activation()

        # Step 1: Load workflow content from URL or attachment
        workflow_dict = _load_workflow_content(trans, workflow_attachment, workflow_url)

        # Check if this is a gxworkflow:// URI reference
        if "workflow_uri" in workflow_dict:
            # Load workflow from Galaxy database using gxworkflow:// URI
            workflow_uri = workflow_dict["workflow_uri"]
            encoded_workflow_id, instance = _parse_gxworkflow_uri(workflow_uri)

            # Load the workflow from the database
            # by_stored_id=not instance means:
            # - False (instance=False) -> load StoredWorkflow (by_stored_id=True)
            # - True (instance=True) -> load Workflow (by_stored_id=False)
            try:
                stored_workflow = self._workflows_service._workflows_manager.get_stored_workflow(
                    trans, encoded_workflow_id, by_stored_id=not instance
                )
            except Exception as e:
                raise exceptions.ObjectNotFound(
                    f"Workflow '{encoded_workflow_id}' not found or not accessible: {str(e)}"
                )

            # Validate user has access to this workflow
            if stored_workflow.user_id != trans.user.id and not trans.user_is_admin:
                raise exceptions.ItemAccessibilityException("You do not have access to this workflow")

            # Use the existing workflow directly - no need to create a new one
            # Skip to step 5 (engine parameters and history)
        else:
            # Step 2: Determine/validate workflow type
            detected_type = _determine_workflow_type(workflow_dict)
            if workflow_type and detected_type != workflow_type:
                raise exceptions.RequestParameterInvalidException(
                    f"Requested workflow type '{workflow_type}' does not match detected type '{detected_type}'"
                )
            workflow_type = detected_type

            # Step 3: Normalize workflow for Galaxy
            raw_workflow_description = _normalize_run_request(
                trans, self._workflows_service._workflow_contents_manager, workflow_dict
            )

            # Step 4: Create workflow in Galaxy
            workflow_create_options = WorkflowCreateOptions(
                archive_source="wes_api",
                fill_defaults=True,
            )
            created_workflow = self._workflows_service._workflow_contents_manager.build_workflow_from_raw_description(
                trans,
                raw_workflow_description,
                workflow_create_options,
                source="WES API",
            )
            stored_workflow = created_workflow.stored_workflow

        # Step 5: Parse engine parameters and create/select history
        engine_params = {}
        if workflow_engine_parameters:
            try:
                engine_params = json.loads(workflow_engine_parameters)
            except json.JSONDecodeError:
                raise exceptions.MessageException("Invalid JSON in workflow_engine_parameters")

        history = _get_or_create_history(trans, engine_params)

        # Step 6: Parse workflow parameters
        invoke_params = {
            "history_id": trans.security.encode_id(history.id),
            "inputs_by": "name",
        }

        if workflow_params:
            try:
                params = json.loads(workflow_params)
                invoke_params["inputs"] = params
            except json.JSONDecodeError:
                raise exceptions.MessageException("Invalid JSON in workflow_params")

        # Step 7: Apply workflow engine parameters
        if "preferred_object_store_id" in engine_params:
            invoke_params["preferred_object_store_id"] = engine_params["preferred_object_store_id"]
        if "use_cached_job" in engine_params:
            invoke_params["use_cached_job"] = engine_params["use_cached_job"].lower() == "true"

        # Step 8: Invoke workflow
        invoke_payload = InvokeWorkflowPayload(**invoke_params)
        workflow_invocation_response = self._workflows_service.invoke_workflow(
            trans,
            trans.security.encode_id(stored_workflow.id),
            invoke_payload,
        )

        # Handle both single and batch responses
        if isinstance(workflow_invocation_response, list):
            raise Exception("Batch workflow invocation not supported in WES API")

        invocation = workflow_invocation_response.root
        encoded_invocation_id = invocation.id
        return self._invocation_id_to_run_id(encoded_invocation_id)

    def list_runs(
        self,
        trans: ProvidesUserContext,
        page_size: int = 10,
        page_token: Optional[str] = None,
    ) -> RunListResponse:
        """List workflow runs for the user with keyset pagination.

        Uses keyset pagination (cursor-based) for stable results even when
        invocations are added/deleted between requests.

        Args:
            trans: Galaxy transaction/context
            page_size: Number of runs per page (default 10, max 100)
            page_token: Keyset token encoding last seen invocation ID

        Returns:
            RunListResponse with paginated list of runs and next_page_token if more results exist
        """
        # Decode keyset token to get last seen ID
        token = self._keyset_pagination.decode_token(page_token, token_class=SingleKeysetToken)
        last_id = token.last_id if token else None

        # Build query with keyset filtering
        query = trans.sa_session.query(WorkflowInvocation).join(History).where(History.user_id == trans.user.id)

        # Apply keyset filter if we have a cursor
        if last_id is not None:
            query = query.filter(WorkflowInvocation.id < last_id)

        # Order by ID desc and fetch page + 1 to detect more results
        invocations = query.order_by(WorkflowInvocation.id.desc()).limit(page_size + 1).all()

        runs = []
        has_more = len(invocations) > page_size
        for invocation in invocations[:page_size]:
            run_summary = self._invocation_to_run_summary(invocation)
            runs.append(run_summary)

        # Generate next_page_token from last item's ID
        next_page_token = None
        if has_more and invocations:
            last_invocation = invocations[page_size - 1]
            token = SingleKeysetToken(last_id=last_invocation.id)
            next_page_token = self._keyset_pagination.encode_token(token)

        return RunListResponse(runs=runs, next_page_token=next_page_token)

    def get_run(
        self,
        trans: SessionRequestContext,
        run_id: int,
    ) -> RunLog:
        """Get full details of a workflow run.

        Args:
            trans: Galaxy transaction/context
            run_id: The WES run ID (Galaxy invocation ID)

        Returns:
            RunLog with complete run details and DRS URIs for outputs
        """
        invocation = self._get_invocation(trans, run_id)
        return self._invocation_to_run_log(trans, invocation)

    def get_run_status(
        self,
        trans: ProvidesUserContext,
        run_id: int,
    ) -> RunStatus:
        """Get abbreviated status of a workflow run.

        Args:
            trans: Galaxy transaction/context
            run_id: The WES run ID (Galaxy invocation ID)

        Returns:
            RunStatus with run ID and current state
        """
        invocation = self._get_invocation(trans, run_id)

        return RunStatus(
            run_id=self.security.encode_id(invocation.id),
            state=GALAXY_TO_WES_STATE.get(invocation.state or "", State.UNKNOWN),
        )

    def cancel_run(
        self,
        trans: ProvidesUserContext,
        run_id: int,
    ) -> RunId:
        """Cancel a running workflow.

        Args:
            trans: Galaxy transaction/context
            run_id: The WES run ID (Galaxy invocation ID)

        Returns:
            RunId of the cancelled run
        """
        invocation = self._get_invocation(trans, run_id)

        # Request cancellation through Galaxy's workflows manager
        cancelled_invocation = self._workflows_service._workflows_manager.request_invocation_cancellation(
            trans, invocation.id
        )
        return self._invocation_to_run_id(cancelled_invocation)

    def _build_task_rows_query(self, invocation_id: int):
        """Build UNION query for all task rows in an invocation.

        Returns a SQLAlchemy Select that produces columns:
        - step_id: int
        - step_order: int
        - task_type: 'single', 'collection', or 'no_job'
        - job_id: Optional[int]
        - job_index: int
        """
        # Subquery 1: Single job steps
        single_jobs = select(
            WorkflowInvocationStep.id.label("step_id"),
            WorkflowInvocationStep.order_index.label("step_order"),
            literal("single").label("task_type"),
            WorkflowInvocationStep.job_id.label("job_id"),
            literal(0).label("job_index"),
        ).where(
            WorkflowInvocationStep.workflow_invocation_id == invocation_id,
            WorkflowInvocationStep.job_id.isnot(None),
        )

        # Subquery 2: Collection mapping job steps (expanded per job)
        collection_jobs = (
            select(
                WorkflowInvocationStep.id.label("step_id"),
                WorkflowInvocationStep.order_index.label("step_order"),
                literal("collection").label("task_type"),
                ImplicitCollectionJobsJobAssociation.job_id.label("job_id"),
                ImplicitCollectionJobsJobAssociation.order_index.label("job_index"),
            )
            .join(
                ImplicitCollectionJobs, WorkflowInvocationStep.implicit_collection_jobs_id == ImplicitCollectionJobs.id
            )
            .join(
                ImplicitCollectionJobsJobAssociation,
                ImplicitCollectionJobs.id == ImplicitCollectionJobsJobAssociation.implicit_collection_jobs_id,
            )
            .where(
                WorkflowInvocationStep.workflow_invocation_id == invocation_id,
                WorkflowInvocationStep.implicit_collection_jobs_id.isnot(None),
            )
        )

        # Subquery 3: No-job steps
        no_jobs = select(
            WorkflowInvocationStep.id.label("step_id"),
            WorkflowInvocationStep.order_index.label("step_order"),
            literal("no_job").label("task_type"),
            literal(None).label("job_id"),
            literal(0).label("job_index"),
        ).where(
            WorkflowInvocationStep.workflow_invocation_id == invocation_id,
            WorkflowInvocationStep.job_id.is_(None),
            WorkflowInvocationStep.implicit_collection_jobs_id.is_(None),
        )

        return union_all(single_jobs, collection_jobs, no_jobs)

    def _get_paginated_task_rows(
        self,
        trans: ProvidesUserContext,
        invocation_id: int,
        last_token: Optional[TaskKeysetToken],
        limit: int,
    ) -> list[dict]:
        """Fetch paginated task rows using composite keyset pagination.

        Uses (step_order, job_index) as composite keyset for cursor-based pagination.

        Returns list of dicts with keys: step_id, step_order, task_type, job_id, job_index
        """
        # Build UNION subquery
        task_rows_subquery = self._build_task_rows_query(invocation_id).subquery()

        # Apply ordering and pagination
        stmt = select(
            task_rows_subquery.c.step_id,
            task_rows_subquery.c.step_order,
            task_rows_subquery.c.task_type,
            task_rows_subquery.c.job_id,
            task_rows_subquery.c.job_index,
        ).order_by(
            task_rows_subquery.c.step_order,
            task_rows_subquery.c.job_index,
        )

        # Apply composite keyset filter if we have a cursor
        if last_token is not None:
            stmt = stmt.where(
                tuple_(
                    task_rows_subquery.c.step_order,
                    task_rows_subquery.c.job_index,
                )
                > tuple_(literal(last_token.step_order), literal(last_token.job_index))
            )

        stmt = stmt.limit(limit + 1)  # Fetch one extra to detect more results

        result = trans.sa_session.execute(stmt)
        return [dict(row._mapping) for row in result]

    def _load_task_objects(
        self,
        trans: ProvidesUserContext,
        task_rows: list[dict],
    ) -> tuple[dict, dict]:
        """Batch load Step and Job objects for task rows.

        Returns:
        - steps_by_id: {step_id: WorkflowInvocationStep}
        - jobs_by_id: {job_id: Job}
        """
        if not task_rows:
            return {}, {}

        # Extract unique IDs
        step_ids = {row["step_id"] for row in task_rows}
        job_ids = {row["job_id"] for row in task_rows if row["job_id"] is not None}

        # Batch load steps with workflow_step relationship
        steps = (
            trans.sa_session.query(WorkflowInvocationStep)
            .options(joinedload(WorkflowInvocationStep.workflow_step))
            .filter(WorkflowInvocationStep.id.in_(step_ids))
            .all()
        )
        steps_by_id = {step.id: step for step in steps}

        # Batch load jobs
        jobs_by_id = {}
        if job_ids:
            jobs = trans.sa_session.query(Job).filter(Job.id.in_(job_ids)).all()
            jobs_by_id = {job.id: job for job in jobs}

        return steps_by_id, jobs_by_id

    def _task_row_to_task_log(
        self,
        task_row: dict,
        steps_by_id: dict,
        jobs_by_id: dict,
    ) -> TaskLog:
        """Convert a task row dict to a TaskLog object.

        Task ID format: order_index or order_index.job_index for collection mapping jobs.
        """
        step_id = task_row["step_id"]
        step_order = task_row["step_order"]
        job_id = task_row["job_id"]
        job_index = task_row["job_index"]
        task_type = task_row["task_type"]

        step = steps_by_id[step_id]
        workflow_step = step.workflow_step

        # Generate task ID using step order_index
        if task_type == "collection":
            task_id = f"{step_order}.{job_index}"
        else:
            task_id = str(step_order)

        # Get step name
        step_name = workflow_step.label or workflow_step.tool_id or f"step_{step.order_index}"

        # Build TaskLog with or without job details
        if job_id is not None:
            job = jobs_by_id[job_id]
            return TaskLog(
                id=task_id,
                name=step_name,
                start_time=job.create_time.isoformat() if job.create_time else None,
                end_time=job.update_time.isoformat() if job.update_time else None,
                stdout=f"/api/jobs/{self._security.encode_id(job.id)}/stdout",
                stderr=f"/api/jobs/{self._security.encode_id(job.id)}/stderr",
                exit_code=job.exit_code,
            )
        else:
            # No job - use step-level timing
            return TaskLog(
                id=task_id,
                name=step_name,
                start_time=step.create_time.isoformat() if step.create_time else None,
                end_time=step.update_time.isoformat() if step.update_time else None,
            )

    def get_run_tasks(
        self,
        trans: ProvidesUserContext,
        run_id: int,
        page_size: int = 10,
        page_token: Optional[str] = None,
    ) -> TaskListResponse:
        """Get paginated list of tasks for a workflow run.

        Uses composite keyset pagination via UNION query to avoid loading
        all steps/jobs into memory and for cursor-based stability.

        Args:
            trans: Galaxy transaction/context
            run_id: The WES run ID (Galaxy invocation ID)
            page_size: Number of tasks per page (default 10, max 100)
            page_token: Token for pagination (composite keyset: step_order, job_index)

        Returns:
            TaskListResponse with paginated tasks
        """
        invocation = self._get_invocation(trans, run_id)

        # Decode composite keyset token
        token = self._keyset_pagination.decode_token(page_token, token_class=TaskKeysetToken)

        # Fetch paginated task rows (+1 to detect more results)
        task_rows = self._get_paginated_task_rows(
            trans,
            invocation.id,
            token,
            page_size,
        )

        # Check if more results exist
        has_more = len(task_rows) > page_size
        if has_more:
            task_rows = task_rows[:page_size]

        # Batch load all needed objects
        steps_by_id, jobs_by_id = self._load_task_objects(trans, task_rows)

        # Convert to TaskLog objects
        task_logs = [self._task_row_to_task_log(row, steps_by_id, jobs_by_id) for row in task_rows]

        # Generate next page token
        next_page_token = None
        if has_more and task_rows:
            last_row = task_rows[-1]
            token = TaskKeysetToken(step_order=last_row["step_order"], job_index=last_row["job_index"])
            next_page_token = self._keyset_pagination.encode_token(token)

        return TaskListResponse(
            task_logs=task_logs if task_logs else None,
            next_page_token=next_page_token,
        )

    def get_run_task(
        self,
        trans: ProvidesUserContext,
        run_id: int,
        task_id: str,
    ) -> TaskLog:
        """Get details for a specific task by direct lookup.

        Parses task_id to extract step order_index and optional job_index,
        then directly queries for that specific step/job.

        Args:
            trans: Galaxy transaction/context
            run_id: The WES run ID (Galaxy invocation ID)
            task_id: Task ID - "{order_index}" or "{order_index}.{job_index}" for collection mapping jobs

        Returns:
            TaskLog object for the specified task

        Raises:
            exceptions.ObjectNotFound: If task not found
        """
        invocation = self._get_invocation(trans, run_id)

        # Parse task_id: either "{order_index}" or "{order_index}.{job_index}"
        parts = task_id.split(".")
        try:
            step_order = int(parts[0])
            job_index = int(parts[1]) if len(parts) > 1 else None
        except (ValueError, IndexError):
            raise exceptions.ObjectNotFound(f"Invalid task_id format: {task_id}")

        # Fetch the specific step by order_index
        step = (
            trans.sa_session.query(WorkflowInvocationStep)
            .options(joinedload(WorkflowInvocationStep.workflow_step))
            .filter(
                WorkflowInvocationStep.order_index == step_order,
                WorkflowInvocationStep.workflow_invocation_id == invocation.id,
            )
            .one_or_none()
        )

        if not step:
            raise exceptions.ObjectNotFound(f"Task {task_id} not found in run {run_id}")

        # Get step name
        workflow_step = step.workflow_step
        step_name = workflow_step.label or workflow_step.tool_id or f"step_{step.order_index}"

        # Handle different step types
        if step.job_id:
            # Single job step
            if job_index is not None:
                raise exceptions.ObjectNotFound(f"Task {task_id} specifies job_index but step has single job")

            job = trans.sa_session.query(Job).filter(Job.id == step.job_id).one()

            return TaskLog(
                id=str(step_order),
                name=step_name,
                start_time=job.create_time.isoformat() if job.create_time else None,
                end_time=job.update_time.isoformat() if job.update_time else None,
                stdout=f"/api/jobs/{self._security.encode_id(job.id)}/stdout",
                stderr=f"/api/jobs/{self._security.encode_id(job.id)}/stderr",
                exit_code=job.exit_code,
            )

        elif step.implicit_collection_jobs_id:
            # Collection mapping job step
            if job_index is None:
                raise exceptions.ObjectNotFound(f"Task {task_id} missing job_index for collection mapping job step")

            # Fetch specific job from collection by order_index
            job_assoc = (
                trans.sa_session.query(ImplicitCollectionJobsJobAssociation)
                .filter(
                    ImplicitCollectionJobsJobAssociation.implicit_collection_jobs_id
                    == step.implicit_collection_jobs_id,
                    ImplicitCollectionJobsJobAssociation.order_index == job_index,
                )
                .one_or_none()
            )

            if not job_assoc:
                raise exceptions.ObjectNotFound(f"Task {task_id} job not found at index {job_index}")

            job = trans.sa_session.query(Job).filter(Job.id == job_assoc.job_id).one()

            return TaskLog(
                id=task_id,
                name=step_name,
                start_time=job.create_time.isoformat() if job.create_time else None,
                end_time=job.update_time.isoformat() if job.update_time else None,
                stdout=f"/api/jobs/{self._security.encode_id(job.id)}/stdout",
                stderr=f"/api/jobs/{self._security.encode_id(job.id)}/stderr",
                exit_code=job.exit_code,
            )

        else:
            # No job step
            if job_index is not None:
                raise exceptions.ObjectNotFound(f"Task {task_id} specifies job_index but step has no jobs")

            return TaskLog(
                id=str(step_order),
                name=step_name,
                start_time=step.create_time.isoformat() if step.create_time else None,
                end_time=step.update_time.isoformat() if step.update_time else None,
            )

    def _invocation_to_run_id(self, invocation: WorkflowInvocation) -> RunId:
        """Convert a WorkflowInvocation to a WES RunId."""
        return self._invocation_id_to_run_id(self._security.encode_id(invocation.id))

    def _invocation_id_to_run_id(self, invocation_id: str) -> RunId:
        """Convert a WorkflowInvocation ID to a WES RunId."""
        return RunId(run_id=invocation_id)

    def _get_invocation(
        self,
        trans: ProvidesUserContext,
        run_id: int,
    ) -> WorkflowInvocation:
        """Get a workflow invocation by ID.

        Args:
            trans: Galaxy transaction/context
            run_id: The invocation ID (unencoded)

        Returns:
            WorkflowInvocation object

        Raises:
            exceptions.ObjectNotFound: If invocation not found
            exceptions.AuthenticationRequired: If user cannot access invocation
        """
        invocation = trans.sa_session.query(WorkflowInvocation).filter_by(id=run_id).one_or_none()

        if not invocation:
            raise exceptions.ObjectNotFound(f"Invocation {run_id} not found")

        if invocation.history.user_id != trans.user.id:
            raise exceptions.AuthenticationRequired(f"Invocation {run_id} not accessible")

        return invocation

    def _invocation_to_run_summary(self, invocation: WorkflowInvocation) -> RunSummary:
        """Convert a Galaxy WorkflowInvocation to a WES RunSummary.

        Args:
            invocation: Galaxy WorkflowInvocation object

        Returns:
            WES RunSummary object
        """
        return RunSummary(
            run_id=self._security.encode_id(invocation.id),
            state=GALAXY_TO_WES_STATE.get(invocation.state or "", State.UNKNOWN),
            start_time=invocation.create_time.isoformat() if invocation.create_time else None,
            end_time=invocation.update_time.isoformat() if invocation.update_time else None,
            tags={},
        )

    def _build_drs_uri(self, trans: SessionRequestContext, dataset_id: int) -> str:
        """Build a DRS URI for a dataset.

        Args:
            trans: Galaxy transaction/context
            dataset_id: Database ID of the dataset

        Returns:
            DRS URI string in format drs://{hostname}/datasets/{encoded_id}
        """
        drs_object_id = f"hda-{trans.security.encode_id(dataset_id, kind='drs')}"
        request_url = trans.request.url
        drs_uri = f"drs://drs.{request_url.components.netloc}/{drs_object_id}"
        return drs_uri

    def _invocation_to_run_log(
        self,
        trans: SessionRequestContext,
        invocation: WorkflowInvocation,
        original_request: Optional[RunRequest] = None,
    ) -> RunLog:
        """Convert a Galaxy WorkflowInvocation to a WES RunLog.

        Args:
            trans: Galaxy transaction/context
            invocation: Galaxy WorkflowInvocation object
            original_request: Original RunRequest if available

        Returns:
            WES RunLog object with outputs and DRS URIs
        """
        # Get invocation outputs formatted as dict
        invocation_dict = invocation.to_dict(view="element")
        outputs_dict = {}

        # Add dataset outputs with DRS URIs
        if "outputs" in invocation_dict:
            for output_name, output_info in invocation_dict["outputs"].items():
                if isinstance(output_info, dict) and output_info.get("src") == "hda":
                    output_id = output_info.get("id")
                    if output_id:
                        output_id_encoded = trans.security.encode_id(output_id)
                        drs_uri = self._build_drs_uri(trans, output_id)
                        output_info["drs_uri"] = drs_uri
                        output_info["id"] = output_id_encoded
                outputs_dict[output_name] = output_info

        # Add collection outputs with DRS URIs
        if "output_collections" in invocation_dict:
            for output_name, output_info in invocation_dict["output_collections"].items():
                if isinstance(output_info, dict) and output_info.get("src") == "hdca":
                    output_id = output_info.get("id")
                    if output_id:
                        output_id_encoded = trans.security.encode_id(output_id)
                        output_info["id"] = output_id_encoded
                outputs_dict[output_name] = output_info

        # Add value outputs as-is
        if "output_values" in invocation_dict:
            outputs_dict.update(invocation_dict["output_values"])

        # Build task logs URL
        encoded_run_id = self._security.encode_id(invocation.id)
        task_logs_url = f"/ga4gh/wes/v1/runs/{encoded_run_id}/tasks"

        # This object has fields related to the workflow run but most of them are geared
        # toward CLI environments - I don't think they make a lot of sense in terms of Galaxy.
        run_log = None

        # Build the RunLog
        # Note: task_logs field is deprecated per WES spec - use task_logs_url instead
        return RunLog(
            run_id=encoded_run_id,
            request=original_request,  # We don't save this so we often can't recover this and that is probably fine. - John
            state=GALAXY_TO_WES_STATE.get(invocation.state or "", State.UNKNOWN),
            run_log=run_log,
            task_logs=None,  # Deprecated field - use task_logs_url
            task_logs_url=task_logs_url,
            outputs=outputs_dict if outputs_dict else None,
        )
