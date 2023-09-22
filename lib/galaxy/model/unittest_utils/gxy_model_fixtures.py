import pytest

from galaxy import model
from galaxy.model.orm.util import add_object_to_object_session
from galaxy.model.unittest_utils.mapping_testing_utils import get_unique_value
from galaxy.model.unittest_utils.model_testing_utils import (
    dbcleanup_wrapper,
    initialize_model,
)


@pytest.fixture(scope="module")
def init_model(engine):
    """Create model objects in the engine's database."""
    # Must use the same engine as the session fixture used by this module.
    initialize_model(model.mapper_registry, engine)


# Fixtures yielding persisted instances of models, deleted from the database on test exit.


@pytest.fixture
def api_keys(session):
    instance = model.APIKeys(key=get_unique_value())
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def cleanup_event(session):
    instance = model.CleanupEvent()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def cloud_authz(session, user, user_authnz_token):
    instance = model.CloudAuthz(user.id, "a", "b", user_authnz_token.id, "c")
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def custos_authnz_token(session, user):
    instance = model.CustosAuthnzToken()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def data_manager_history_association(session):
    instance = model.DataManagerHistoryAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def data_manager_job_association(session):
    instance = model.DataManagerJobAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def dataset(session):
    instance = model.Dataset()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def dataset_collection(session):
    instance = model.DatasetCollection(collection_type="a")
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def dataset_collection_element(session, dataset_collection, history_dataset_association):
    instance = model.DatasetCollectionElement(collection=dataset_collection, element=history_dataset_association)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def dataset_hash(session):
    instance = model.DatasetHash()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def dataset_permission(session, dataset):
    instance = model.DatasetPermissions("a", dataset)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def dataset_source(session):
    instance = model.DatasetSource()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def dataset_source_hash(session):
    instance = model.DatasetSourceHash()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def default_history_permissions(session, history, role):
    instance = model.DefaultHistoryPermissions(history, "a", role)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def default_quota_association(session, quota):
    type_ = model.DefaultQuotaAssociation.types.REGISTERED
    instance = model.DefaultQuotaAssociation(type_, quota)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def default_user_permissions(session, user, role):
    instance = model.DefaultUserPermissions(user, None, role)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def dynamic_tool(session):
    instance = model.DynamicTool()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def extended_metadata(session):
    instance = model.ExtendedMetadata(None)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def extended_metadata_index(session, extended_metadata):
    instance = model.ExtendedMetadataIndex(extended_metadata, None, None)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def form_definition(session, form_definition_current):
    instance = model.FormDefinition(name="a", form_definition_current=form_definition_current)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def form_definition_current(session):
    instance = model.FormDefinitionCurrent()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def form_values(session):
    instance = model.FormValues()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def galaxy_session(session):
    instance = model.GalaxySession(session_key=get_unique_value())
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def galaxy_session_history_association(session, galaxy_session, history):
    instance = model.GalaxySessionToHistoryAssociation(galaxy_session, history)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def group(session):
    instance = model.Group(name=get_unique_value())
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def group_quota_association(session):
    instance = model.GroupQuotaAssociation(None, None)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def group_role_association(session):
    instance = model.GroupRoleAssociation(None, None)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def history(session):
    instance = model.History()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def history_annotation_association(session):
    instance = model.HistoryAnnotationAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def history_dataset_association(session, dataset):
    instance = model.HistoryDatasetAssociation(dataset=dataset)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def history_dataset_association_annotation_association(session):
    instance = model.HistoryDatasetAssociationAnnotationAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def history_dataset_association_rating_association(session):
    instance = model.HistoryDatasetAssociationRatingAssociation(None, None)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def history_dataset_association_tag_association(session):
    instance = model.HistoryDatasetAssociationTagAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def history_dataset_collection_annotation_association(session):
    instance = model.HistoryDatasetCollectionAssociationAnnotationAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def history_dataset_collection_association(session):
    instance = model.HistoryDatasetCollectionAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def history_dataset_collection_rating_association(
    session,
    user,
    history_dataset_collection_association,
):
    instance = model.HistoryDatasetCollectionRatingAssociation(user, history_dataset_collection_association)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def history_dataset_collection_tag_association(session):
    instance = model.HistoryDatasetCollectionTagAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def history_rating_association(session, user, history):
    instance = model.HistoryRatingAssociation(user, history)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def history_tag_association(session):
    instance = model.HistoryTagAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def history_user_share_association(session):
    instance = model.HistoryUserShareAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def implicit_collection_jobs(session):
    instance = model.ImplicitCollectionJobs(populated_state="new")
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def implicit_collection_jobs_job_association(session):
    instance = model.ImplicitCollectionJobsJobAssociation()
    instance.order_index = 1
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def implicitly_converted_dataset_association(session, history_dataset_association):
    instance = model.ImplicitlyConvertedDatasetAssociation(
        dataset=history_dataset_association,
        parent=history_dataset_association,  # using the same dataset; should work here.
    )
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def implicitly_created_dataset_collection_input(session, history_dataset_collection_association):
    instance = model.ImplicitlyCreatedDatasetCollectionInput(None, history_dataset_collection_association)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def interactive_tool_entry_point(session):
    instance = model.InteractiveToolEntryPoint()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def job(session):
    instance = model.Job()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def job_container_association(session):
    instance = model.JobContainerAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def job_export_history_archive(session):
    instance = model.JobExportHistoryArchive()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def job_external_output_metadata(session, job, history_dataset_association):
    instance = model.JobExternalOutputMetadata(job, history_dataset_association)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def job_metric_numeric(session):
    instance = model.JobMetricNumeric(None, None, None)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def job_metric_text(session):
    instance = model.JobMetricText(None, None, None)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def job_parameter(session):
    instance = model.JobParameter(None, None)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def job_state_history(session, job):
    instance = model.JobStateHistory(job)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def job_to_implicit_output_dataset_collection_association(session, dataset_collection):
    instance = model.JobToImplicitOutputDatasetCollectionAssociation(None, dataset_collection)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def job_to_input_dataset_association(session, history_dataset_association):
    instance = model.JobToInputDatasetAssociation(None, history_dataset_association)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def job_to_input_dataset_collection_association(session, history_dataset_collection_association):
    instance = model.JobToInputDatasetCollectionAssociation(None, history_dataset_collection_association)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def job_to_input_dataset_collection_element_association(session, dataset_collection_element):
    instance = model.JobToInputDatasetCollectionElementAssociation(None, dataset_collection_element)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def job_to_input_library_dataset_association(session, library_dataset_dataset_association):
    instance = model.JobToInputLibraryDatasetAssociation(None, library_dataset_dataset_association)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def job_to_output_dataset_association(session, history_dataset_association):
    instance = model.JobToOutputDatasetAssociation(None, history_dataset_association)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def job_to_output_dataset_collection_association(session, history_dataset_collection_association):
    instance = model.JobToOutputDatasetCollectionAssociation(None, history_dataset_collection_association)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def job_to_output_library_dataset_association(session, library_dataset_dataset_association):
    instance = model.JobToOutputLibraryDatasetAssociation(None, library_dataset_dataset_association)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def library(session):
    instance = model.Library()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def library_dataset(session, library_dataset_dataset_association):
    instance = model.LibraryDataset(library_dataset_dataset_association=library_dataset_dataset_association)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def library_dataset_collection_annotation_association(session):
    instance = model.LibraryDatasetCollectionAnnotationAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def library_dataset_collection_association(session):
    instance = model.LibraryDatasetCollectionAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def library_dataset_collection_rating_association(session):
    instance = model.LibraryDatasetCollectionRatingAssociation(None, None)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def library_dataset_collection_tag_association(session):
    instance = model.LibraryDatasetCollectionTagAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def library_dataset_dataset_association(session):
    instance = model.LibraryDatasetDatasetAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def library_dataset_dataset_association_permission(session, library_dataset_dataset_association, role):
    instance = model.LibraryDatasetDatasetAssociationPermissions("a", library_dataset_dataset_association, role)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def library_dataset_dataset_association_tag_association(session):
    instance = model.LibraryDatasetDatasetAssociationTagAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def library_dataset_permission(session, library_dataset, role):
    instance = model.LibraryDatasetPermissions("a", library_dataset, role)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def library_folder(session):
    instance = model.LibraryFolder()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def library_folder_permission(session, library_folder, role):
    instance = model.LibraryFolderPermissions("a", library_folder, role)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def library_permission(session, library, role):
    instance = model.LibraryPermissions("a", library, role)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def metadata_file(session):
    instance = model.MetadataFile()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def page(session, user):
    instance = model.Page()
    instance.user = user
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def page_annotation_association(session):
    instance = model.PageAnnotationAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def page_rating_association(session):
    instance = model.PageRatingAssociation(None, None)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def page_revision(session, page):
    instance = model.PageRevision()
    instance.page = page
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def page_tag_association(session):
    instance = model.PageTagAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def page_user_share_association(session):
    instance = model.PageUserShareAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def post_job_action(session):
    instance = model.PostJobAction("a")
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def post_job_action_association(session, post_job_action, job):
    instance = model.PostJobActionAssociation(post_job_action, job)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def quota(session):
    instance = model.Quota(get_unique_value(), "b")
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def role(session):
    instance = model.Role(name=get_unique_value())
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def stored_workflow(session, user):
    instance = model.StoredWorkflow()
    add_object_to_object_session(instance, user)
    instance.user = user
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def stored_workflow_annotation_association(session):
    instance = model.StoredWorkflowAnnotationAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def stored_workflow_rating_association(session):
    instance = model.StoredWorkflowRatingAssociation(None, None)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def stored_workflow_tag_association(session):
    instance = model.StoredWorkflowTagAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def stored_workflow_user_share_association(session):
    instance = model.StoredWorkflowUserShareAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def tag(session):
    instance = model.Tag()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def task(session, job):
    instance = model.Task(job, "a", "b")
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def task_metric_numeric(session):
    instance = model.TaskMetricNumeric("a", "b", 9)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def task_metric_text(session):
    instance = model.TaskMetricText("a", "b", "c")
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def tool_tag_association(session):
    instance = model.ToolTagAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def user(session):
    instance = model.User(email=get_unique_value(), password="password")
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def user_address(session):
    instance = model.UserAddress()
    instance.name = "a"
    instance.address = "b"
    instance.city = "c"
    instance.state = "d"
    instance.postal_code = "e"
    instance.country = "f"
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def user_authnz_token(session, user):
    instance = model.UserAuthnzToken("a", "b", "c", 1, "d", user)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def user_group_association(session):
    instance = model.UserGroupAssociation(None, None)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def user_preference(session):
    instance = model.UserPreference()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def user_quota_association(session):
    instance = model.UserQuotaAssociation(None, None)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def user_role_association(session, user, role):
    instance = model.UserRoleAssociation(user, role)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def visualization(session, user):
    instance = model.Visualization()
    instance.user = user
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def visualization_annotation_association(session):
    instance = model.VisualizationAnnotationAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def visualization_rating_association(session, user, visualization):
    instance = model.VisualizationRatingAssociation(user, visualization)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def visualization_revision(session, visualization):
    instance = model.VisualizationRevision(visualization_id=visualization.id)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def visualization_tag_association(session):
    instance = model.VisualizationTagAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def visualization_user_share_association(session):
    instance = model.VisualizationUserShareAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def workflow(session):
    instance = model.Workflow()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def workflow_invocation(session, workflow):
    instance = model.WorkflowInvocation()
    instance.workflow = workflow
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def workflow_invocation_output_dataset_association(session):
    instance = model.WorkflowInvocationOutputDatasetAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def workflow_invocation_output_dataset_collection_association(session):
    instance = model.WorkflowInvocationOutputDatasetCollectionAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def workflow_invocation_output_value(session):
    instance = model.WorkflowInvocationOutputValue()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def workflow_invocation_step(session, workflow_invocation, workflow_step):
    instance = model.WorkflowInvocationStep()
    instance.workflow_invocation = workflow_invocation
    instance.workflow_step = workflow_step
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def workflow_invocation_step_output_dataset_association(session):
    instance = model.WorkflowInvocationStepOutputDatasetAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def workflow_invocation_step_output_dataset_collection_association(session):
    instance = model.WorkflowInvocationStepOutputDatasetCollectionAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def workflow_output(session, workflow_step):
    instance = model.WorkflowOutput(workflow_step)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def workflow_request_input_parameter(session):
    instance = model.WorkflowRequestInputParameter()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def workflow_request_input_step_parameter(session):
    instance = model.WorkflowRequestInputStepParameter()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def workflow_request_step_state(session):
    instance = model.WorkflowRequestStepState()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def workflow_request_to_input_dataset_association(session):
    instance = model.WorkflowRequestToInputDatasetAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def workflow_request_to_input_dataset_collection_association(session):
    instance = model.WorkflowRequestToInputDatasetCollectionAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def workflow_step(session, workflow):
    instance = model.WorkflowStep()
    add_object_to_object_session(instance, workflow)
    instance.workflow = workflow
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def workflow_step_annotation_association(session):
    instance = model.WorkflowStepAnnotationAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def workflow_step_connection(session):
    instance = model.WorkflowStepConnection()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def workflow_step_input(session, workflow_step):
    instance = model.WorkflowStepInput(workflow_step)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def workflow_step_tag_association(session):
    instance = model.WorkflowStepTagAssociation()
    yield from dbcleanup_wrapper(session, instance)


# Fixtures yielding factory functions.
# In some tests we may need more than one instance of the same model. We cannot reuse a model
# fixture, and we cannot pass multiple copies of the same fixture to one test. We have to
# instantiate a new instance of the model inside the test. However, a test should only know
# how to construct the model it is testing, so instead of constructing an object directly,
# a test calls a factory function, passed to it as a fixture.


@pytest.fixture
def dataset_collection_factory():
    def make_instance(*args, **kwds):
        if "collection_type" not in kwds:
            kwds["collection_type"] = "a"
        return model.DatasetCollection(*args, **kwds)

    return make_instance


@pytest.fixture
def history_dataset_association_factory():
    def make_instance(*args, **kwds):
        return model.HistoryDatasetAssociation(*args, **kwds)

    return make_instance


@pytest.fixture
def history_dataset_collection_association_factory():
    def make_instance(*args, **kwds):
        return model.HistoryDatasetCollectionAssociation(*args, **kwds)

    return make_instance


@pytest.fixture
def history_factory():
    def make_instance(**kwds):
        instance = model.History()
        if "deleted" in kwds:
            instance.deleted = kwds["deleted"]
        return instance

    return make_instance


@pytest.fixture
def history_rating_association_factory():
    def make_instance(*args, **kwds):
        return model.HistoryRatingAssociation(*args, **kwds)

    return make_instance


@pytest.fixture
def implicitly_converted_dataset_association_factory(history_dataset_association):
    def make_instance(*args, **kwds):
        instance = model.ImplicitlyConvertedDatasetAssociation(
            dataset=history_dataset_association,
            parent=history_dataset_association,  # using the same dataset; should work here.
        )
        return instance

    return make_instance


@pytest.fixture
def library_dataset_dataset_association_factory():
    def make_instance(*args, **kwds):
        return model.LibraryDatasetDatasetAssociation(*args, **kwds)

    return make_instance


@pytest.fixture
def library_folder_factory():
    def make_instance(*args, **kwds):
        return model.LibraryFolder(*args, **kwds)

    return make_instance


@pytest.fixture
def page_rating_association_factory():
    def make_instance(*args, **kwds):
        return model.PageRatingAssociation(*args, **kwds)

    return make_instance


@pytest.fixture
def role_factory():
    def make_instance(*args, **kwds):
        return model.Role(*args, **kwds)

    return make_instance


@pytest.fixture
def stored_workflow_menu_entry_factory():
    def make_instance(*args, **kwds):
        return model.StoredWorkflowMenuEntry(*args, **kwds)

    return make_instance


@pytest.fixture
def stored_workflow_rating_association_factory():
    def make_instance(*args, **kwds):
        return model.StoredWorkflowRatingAssociation(*args, **kwds)

    return make_instance


@pytest.fixture
def stored_workflow_tag_association_factory():
    def make_instance(*args, **kwds):
        return model.StoredWorkflowTagAssociation(*args, **kwds)

    return make_instance


@pytest.fixture
def user_role_association_factory():
    def make_instance(*args, **kwds):
        return model.UserRoleAssociation(*args, **kwds)

    return make_instance


@pytest.fixture
def visualization_rating_association_factory():
    def make_instance(*args, **kwds):
        return model.VisualizationRatingAssociation(*args, **kwds)

    return make_instance


@pytest.fixture
def visualization_revision_factory(visualization):
    def make_instance(*args, **kwds):
        if "visualization_id" not in kwds:
            kwds["visualization_id"] = visualization.id
        return model.VisualizationRevision(*args, **kwds)

    return make_instance


@pytest.fixture
def workflow_factory():
    def make_instance(*args, **kwds):
        return model.Workflow(*args, **kwds)

    return make_instance


@pytest.fixture
def workflow_invocation_factory(workflow):
    def make_instance(**kwds):
        instance = model.WorkflowInvocation()
        instance.workflow = kwds.get("workflow", workflow)
        return instance

    return make_instance


@pytest.fixture
def workflow_invocation_to_subworkflow_invocation_association_factory():
    def make_instance(*args, **kwds):
        return model.WorkflowInvocationToSubworkflowInvocationAssociation(*args, **kwds)

    return make_instance


@pytest.fixture
def workflow_step_connection_factory():
    def make_instance(*args, **kwds):
        return model.WorkflowStepConnection(*args, **kwds)

    return make_instance


@pytest.fixture
def workflow_step_factory(workflow):
    def make_instance(*args, **kwds):
        instance = model.WorkflowStep()
        workflow2 = kwds.get("workflow", workflow)  # rename workflow not to confuse pytest
        add_object_to_object_session(instance, workflow2)
        instance.workflow = workflow2
        instance.subworkflow = kwds.get("subworkflow")
        return instance

    return make_instance
