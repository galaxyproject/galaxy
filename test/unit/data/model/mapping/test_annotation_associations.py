import pytest

from galaxy import model
from ..testing_utils import (  # noqa: F401
    create_and_drop_database,
    dbcleanup,
    disposing_engine,
    get_plugin_full_name,
    get_stored_obj,
    url,
)

model_fixtures = get_plugin_full_name("mapping.testing_utils.gxy_model_fixtures")
pytest_plugins = [model_fixtures]


@pytest.fixture(scope="module")
def engine(url):  # noqa: F811
    with create_and_drop_database(url):
        with disposing_engine(url) as engine:
            yield engine


def test_history_annotation_associations(session, history_annotation_association, user, history):
    _annotation_assoc_helper(
        session, history_annotation_association, user, history, "history", model.HistoryAnnotationAssociation
    )


def test_history_dataset_association_annotation_associations(
    session, history_dataset_association_annotation_association, user, history_dataset_association
):
    _annotation_assoc_helper(
        session,
        history_dataset_association_annotation_association,
        user,
        history_dataset_association,
        "hda",
        model.HistoryDatasetAssociationAnnotationAssociation,
    )


def test_stored_workflow_annotation_associations(
    session,
    stored_workflow_annotation_association,
    user,
    stored_workflow,
):
    _annotation_assoc_helper(
        session,
        stored_workflow_annotation_association,
        user,
        stored_workflow,
        "stored_workflow",
        model.StoredWorkflowAnnotationAssociation,
    )


def test_workflow_step_annotation_associations(session, workflow_step_annotation_association, user, workflow_step):
    _annotation_assoc_helper(
        session,
        workflow_step_annotation_association,
        user,
        workflow_step,
        "workflow_step",
        model.WorkflowStepAnnotationAssociation,
    )


def test_page_annotation_associations(session, page_annotation_association, user, page):
    _annotation_assoc_helper(session, page_annotation_association, user, page, "page", model.PageAnnotationAssociation)


def test_visualization_annotation_associations(session, visualization_annotation_association, user, visualization):
    _annotation_assoc_helper(
        session,
        visualization_annotation_association,
        user,
        visualization,
        "visualization",
        model.VisualizationAnnotationAssociation,
    )


def test_history_dataset_collection_association_annotation_associations(
    session, history_dataset_collection_annotation_association, user, history_dataset_collection_association
):
    _annotation_assoc_helper(
        session,
        history_dataset_collection_annotation_association,
        user,
        history_dataset_collection_association,
        "history_dataset_collection",
        model.HistoryDatasetCollectionAssociationAnnotationAssociation,
    )


def test_library_dataset_collection_annotation_associations(
    session, library_dataset_collection_annotation_association, user, library_dataset_collection_association
):
    _annotation_assoc_helper(
        session,
        library_dataset_collection_annotation_association,
        user,
        library_dataset_collection_association,
        "dataset_collection",
        model.LibraryDatasetCollectionAnnotationAssociation,
    )


def _annotation_assoc_helper(session, association, user, assoc_object, assoc_object_name, cls_):
    annotation = "a"
    setattr(association, assoc_object_name, assoc_object)  # FooAnnotAssoc.foo
    association.annotation = annotation  # FooAnnotAssoc.annotation
    association.user = user  # FooAnnotAssoc.user

    with dbcleanup(session, association) as id:
        stored_obj = get_stored_obj(session, cls_, id)
        assert stored_obj.id == id
        _stored_assoc_object = getattr(stored_obj, assoc_object_name)
        assert _stored_assoc_object.id == assoc_object.id
        assert stored_obj.annotation == annotation
        assert stored_obj.user_id == user.id
