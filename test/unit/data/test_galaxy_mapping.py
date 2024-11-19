import os
import random
import uuid
from tempfile import NamedTemporaryFile
from typing import List

import pytest
from sqlalchemy import (
    inspect,
    select,
)

import galaxy.datatypes.registry
import galaxy.model
import galaxy.model.mapping as mapping
from galaxy import model
from galaxy.model.base import transaction
from galaxy.model.database_utils import create_database
from galaxy.model.metadata import MetadataTempFile
from galaxy.model.orm.util import (
    add_object_to_object_session,
    get_object_session,
)
from galaxy.model.security import GalaxyRBACAgent
from galaxy.model.unittest_utils.utils import random_email
from galaxy.objectstore import QuotaSourceMap
from galaxy.util.unittest import TestCase

datatypes_registry = galaxy.datatypes.registry.Registry()
datatypes_registry.load_datatypes()
galaxy.model.set_datatypes_registry(datatypes_registry)

DB_URI = "sqlite:///:memory:"
# docker run -e POSTGRES_USER=galaxy -p 5432:5432 -d postgres
# GALAXY_TEST_UNIT_MAPPING_URI_POSTGRES_BASE='postgresql://galaxy@localhost:5432/' pytest test/unit/data/test_galaxy_mapping.py
skip_if_not_postgres_base = pytest.mark.skipif(
    not os.environ.get("GALAXY_TEST_UNIT_MAPPING_URI_POSTGRES_BASE"),
    reason="GALAXY_TEST_UNIT_MAPPING_URI_POSTGRES_BASE not set",
)
PRIVATE_OBJECT_STORE_ID = "my_private_data"


class BaseModelTestCase(TestCase):
    model: mapping.GalaxyModelMapping

    @classmethod
    def _db_uri(cls):
        return DB_URI

    @classmethod
    def setUpClass(cls):
        # Start the database and connect the mapping
        cls.model = mapping.init("/tmp", cls._db_uri(), create_tables=True)
        model.setup_global_object_store_for_models(MockObjectStore())
        assert cls.model.engine is not None

    @classmethod
    def persist(cls, *args, **kwargs):
        session = cls.session()
        commit = kwargs.get("commit", True)
        for arg in args:
            session.add(arg)
            if commit:
                session.commit()
        if kwargs.get("expunge", not commit):
            cls.expunge()
        return arg  # Return last or only arg.

    @classmethod
    def session(cls):
        return cls.model.session

    @classmethod
    def expunge(cls):
        cls.model.session.flush()
        cls.model.session.expunge_all()


class TestMappings(BaseModelTestCase):

    def test_dataset_instance_order(self) -> None:
        u = model.User(email=random_email(), password="password")
        h1 = model.History(name="History 1", user=u)
        elements = []
        list_pair = model.DatasetCollection(collection_type="list:paired")
        for i in range(20):
            pair = model.DatasetCollection(collection_type="pair")
            forward = model.HistoryDatasetAssociation(
                extension="txt", history=h1, name=f"forward_{i}", create_dataset=True, sa_session=self.model.session
            )
            reverse = model.HistoryDatasetAssociation(
                extension="bam", history=h1, name=f"reverse_{i}", create_dataset=True, sa_session=self.model.session
            )
            dce1 = model.DatasetCollectionElement(
                collection=pair, element=forward, element_identifier=f"forward_{i}", element_index=1
            )
            dce2 = model.DatasetCollectionElement(
                collection=pair, element=reverse, element_identifier=f"reverse_{i}", element_index=2
            )
            to_persist = [(forward, reverse), (dce1, dce2)]
            self.persist(pair)
            for pair_item in to_persist:
                if i % 2:
                    self.persist(pair_item[0])
                    self.persist(pair_item[1])
                else:
                    self.persist(pair_item[1])
                    self.persist(pair_item[0])
            elements.append(
                model.DatasetCollectionElement(
                    collection=list_pair, element=pair, element_index=i, element_identifier=str(i)
                )
            )
        self.persist(list_pair)
        random.shuffle(elements)
        for item in elements:
            self.persist(item)
        forward_hdas: List[model.HistoryDatasetAssociation] = []
        reverse_hdas: List[model.HistoryDatasetAssociation] = []
        for i, dataset_instance in enumerate(list_pair.dataset_instances):
            if i % 2:
                reverse_hdas.append(dataset_instance)
            else:
                forward_hdas.append(dataset_instance)
        assert all(d.name == f"forward_{i}" for i, d in enumerate(forward_hdas))
        assert all(d.name == f"reverse_{i}" for i, d in enumerate(reverse_hdas))

    def test_nested_collection_attributes(self):
        u = model.User(email="mary2@example.com", password="password")
        h1 = model.History(name="History 1", user=u)
        d1 = model.HistoryDatasetAssociation(
            extension="bam", history=h1, create_dataset=True, sa_session=self.model.session
        )
        index = NamedTemporaryFile("w")
        index.write("cool bam index")
        index2 = NamedTemporaryFile("w")
        index2.write("cool bam index 2")
        metadata_dict = {
            "bam_index": MetadataTempFile.from_JSON({"kwds": {}, "filename": index.name}),
            "bam_csi_index": MetadataTempFile.from_JSON({"kwds": {}, "filename": index2.name}),
        }
        d1.metadata.from_JSON_dict(json_dict=metadata_dict)
        assert d1.metadata.bam_index
        assert d1.metadata.bam_csi_index
        assert isinstance(d1.metadata.bam_index, model.MetadataFile)
        assert isinstance(d1.metadata.bam_csi_index, model.MetadataFile)
        d2 = model.HistoryDatasetAssociation(
            extension="txt", history=h1, create_dataset=True, sa_session=self.model.session
        )
        c1 = model.DatasetCollection(collection_type="paired")
        dce1 = model.DatasetCollectionElement(collection=c1, element=d1, element_identifier="forward", element_index=0)
        dce2 = model.DatasetCollectionElement(collection=c1, element=d2, element_identifier="reverse", element_index=1)
        c2 = model.DatasetCollection(collection_type="list:paired")
        dce3 = model.DatasetCollectionElement(
            collection=c2, element=c1, element_identifier="inner_list", element_index=0
        )
        c3 = model.DatasetCollection(collection_type="list:list")
        c4 = model.DatasetCollection(collection_type="list:list:paired")
        dce4 = model.DatasetCollectionElement(
            collection=c4, element=c2, element_identifier="outer_list", element_index=0
        )
        self.model.session.add_all([d1, d2, c1, dce1, dce2, c2, dce3, c3, c4, dce4])
        self.model.session.flush()

        stmt = c2._build_nested_collection_attributes_stmt(
            element_attributes=("element_identifier",), hda_attributes=("extension",), dataset_attributes=("state",)
        )
        result = self.model.session.execute(stmt).all()
        assert [(r._fields) for r in result] == [
            ("element_identifier_0", "element_identifier_1", "extension", "state"),
            ("element_identifier_0", "element_identifier_1", "extension", "state"),
        ]

        stmt = c2._build_nested_collection_attributes_stmt(
            element_attributes=("element_identifier",), hda_attributes=("extension",), dataset_attributes=("state",)
        )
        result = self.model.session.execute(stmt).all()
        assert result == [("inner_list", "forward", "bam", "new"), ("inner_list", "reverse", "txt", "new")]

        stmt = c2._build_nested_collection_attributes_stmt(return_entities=(model.HistoryDatasetAssociation,))
        result = self.model.session.execute(stmt).all()
        assert result == [(d1,), (d2,)]

        stmt = c2._build_nested_collection_attributes_stmt(
            return_entities=(model.HistoryDatasetAssociation, model.Dataset)
        )
        result = self.model.session.execute(stmt).all()
        assert result == [(d1, d1.dataset), (d2, d2.dataset)]
        # Assert properties that use _get_nested_collection_attributes return correct content
        assert c2.dataset_instances == [d1, d2]
        assert c2.dataset_elements == [dce1, dce2]
        assert c2.dataset_action_tuples == []
        assert c2.populated_optimized
        assert c2.dataset_states_and_extensions_summary == ({"new"}, {"txt", "bam"})
        assert c2.element_identifiers_extensions_paths_and_metadata_files == [
            [
                ("inner_list", "forward"),
                "bam",
                "mock_dataset_14.dat",
                [("bai", "mock_dataset_14.dat"), ("bam.csi", "mock_dataset_14.dat")],
            ],
            [("inner_list", "reverse"), "txt", "mock_dataset_14.dat", []],
        ]
        assert c3.dataset_instances == []
        assert c3.dataset_elements == []
        assert c3.dataset_states_and_extensions_summary == (set(), set())

        stmt = c4._build_nested_collection_attributes_stmt(element_attributes=("element_identifier",))
        result = self.model.session.execute(stmt).all()
        assert result == [
            ("outer_list", "inner_list", "forward"),
            ("outer_list", "inner_list", "reverse"),
        ]
        assert c4.dataset_elements == [dce1, dce2]

    def test_history_audit(self):
        u = model.User(email=random_email(), password="password")
        h1 = model.History(name="HistoryAuditHistory", user=u)
        h2 = model.History(name="HistoryAuditHistory", user=u)

        def get_audit_table_entries(history):
            stmt = select(model.HistoryAudit.table).filter(model.HistoryAudit.table.c.history_id == history.id)
            return self.session().execute(stmt).all()

        def get_latest_entry(entries):
            # key ensures result is correct if new columns are added
            return max(entries, key=lambda x: x.update_time)

        self.persist(u, h1, h2, expunge=False)
        assert len(get_audit_table_entries(h1)) == 1
        assert len(get_audit_table_entries(h2)) == 1

        self.new_hda(h1, name="1")
        self.new_hda(h2, name="2")

        session = self.session()

        with transaction(session):
            session.commit()
        # _next_hid modifies history, plus trigger on HDA means 2 additional audit rows per history

        h1_audits = get_audit_table_entries(h1)
        h2_audits = get_audit_table_entries(h2)
        assert len(h1_audits) == 3
        assert len(h2_audits) == 3

        h1_latest = get_latest_entry(h1_audits)
        h2_latest = get_latest_entry(h2_audits)

        # In galaxy, HistoryAudit.prune() executes in the context of a separate thread, where it
        # starts and commits a new transaction, closing a scoped session on exit. Thus, here we
        # should end the current transaction (via rollback) and add the History objects to a new
        # session, as the previous one will be closed.
        session.rollback()
        model.HistoryAudit.prune(session)
        session.add_all([h1, h2])

        h1_audits = get_audit_table_entries(h1)
        h2_audits = get_audit_table_entries(h2)
        assert len(h1_audits) == 1
        assert len(h2_audits) == 1
        assert h1_audits[0] == h1_latest
        assert h2_audits[0] == h2_latest

    def _non_empty_flush(self):
        lf = model.LibraryFolder(name="RootFolder")
        session = self.session()
        session.add(lf)
        session.flush()

    def test_flush_refreshes(self):
        # Normally I don't believe in unit testing library code, but the behaviors around attribute
        # states and flushing in SQL Alchemy is very subtle and it is good to have a executable
        # reference for how it behaves in the context of Galaxy objects.
        model = self.model
        user = model.User(email=random_email(), password="password")
        galaxy_session = model.GalaxySession()
        galaxy_session_other = model.GalaxySession()
        galaxy_session.user = user
        galaxy_session_other.user = user
        self.persist(user, galaxy_session_other, galaxy_session)
        galaxy_session_id = galaxy_session.id

        self.expunge()
        session = self.session()
        galaxy_model_object = self.model.session.get(model.GalaxySession, galaxy_session_id)
        expected_id = galaxy_model_object.id

        # id loaded as part of the object query, could be any non-deferred attribute.
        assert "id" not in inspect(galaxy_model_object).unloaded

        # Perform an empty flush, verify empty flush doesn't reload all attributes.
        session.flush()
        assert "id" not in inspect(galaxy_model_object).unloaded

        # However, flushing anything non-empty - even unrelated object will invalidate
        # the session ID.
        self._non_empty_flush()
        if session().in_transaction():
            session.commit()
        assert "id" in inspect(galaxy_model_object).unloaded

        # Fetch the ID loads the value from the database
        assert expected_id == galaxy_model_object.id
        assert "id" not in inspect(galaxy_model_object).unloaded

        # Using cached_id instead does not exhibit this behavior.
        self._non_empty_flush()
        if session().in_transaction():
            session.commit()
        assert expected_id == galaxy.model.cached_id(galaxy_model_object)
        assert "id" in inspect(galaxy_model_object).unloaded

        # Keeping the following failed experiments here for future reference,
        # I probed the internals of the attribute tracking and couldn't find an
        # alternative, generalized way to get the previously loaded value for unloaded
        # attributes.
        # print(galaxy_model_object._sa_instance_state.attrs.id)
        # print(dir(galaxy_model_object._sa_instance_state.attrs.id))
        # print(galaxy_model_object._sa_instance_state.attrs.id.loaded_value)
        # print(galaxy_model_object._sa_instance_state.attrs.id.state)
        # print(galaxy_model_object._sa_instance_state.attrs.id.load_history())
        # print(dir(galaxy_model_object._sa_instance_state.attrs.id.load_history()))
        # print(galaxy_model_object._sa_instance_state.identity)
        # print(dir(galaxy_model_object._sa_instance_state))
        # print(galaxy_model_object._sa_instance_state.expired_attributes)
        # print(galaxy_model_object._sa_instance_state.expired)
        # print(galaxy_model_object._sa_instance_state._instance_dict().keys())
        # print(dir(galaxy_model_object._sa_instance_state._instance_dict))
        # assert False

        # Verify cached_id works even immediately after an initial flush, prevents a second SELECT
        # query that would be executed if object.id was used.
        galaxy_model_object_new = model.GalaxySession()
        session.add(galaxy_model_object_new)
        session.flush()
        if session().in_transaction():
            session.commit()
        assert galaxy.model.cached_id(galaxy_model_object_new)
        assert "id" in inspect(galaxy_model_object_new).unloaded

        # Verify a targeted flush prevent expiring unrelated objects.
        galaxy_model_object_new.id  # noqa: B018
        assert "id" not in inspect(galaxy_model_object_new).unloaded
        session.flush(model.GalaxySession())
        assert "id" not in inspect(galaxy_model_object_new).unloaded

    def test_workflows(self):
        user = model.User(email=random_email(), password="password")

        child_workflow = _workflow_from_steps(user, [])
        self.persist(child_workflow)

        workflow_step_1 = model.WorkflowStep()
        workflow_step_1.order_index = 0
        workflow_step_1.type = "data_input"
        workflow_step_2 = model.WorkflowStep()
        workflow_step_2.order_index = 1
        workflow_step_2.type = "subworkflow"
        add_object_to_object_session(workflow_step_2, child_workflow)
        workflow_step_2.subworkflow = child_workflow

        workflow_step_1.get_or_add_input("moo1")
        workflow_step_1.get_or_add_input("moo2")
        workflow_step_2.get_or_add_input("moo")
        workflow_step_1.add_connection("foo", "cow", workflow_step_2)

        workflow = _workflow_from_steps(user, [workflow_step_1, workflow_step_2])
        self.persist(workflow)
        workflow_id = workflow.id

        annotation = model.WorkflowStepAnnotationAssociation()
        annotation.annotation = "Test Step Annotation"
        annotation.user = user
        add_object_to_object_session(annotation, workflow_step_1)
        annotation.workflow_step = workflow_step_1
        self.persist(annotation)

        assert workflow_step_1.id is not None
        workflow_invocation = _invocation_for_workflow(user, workflow)

        invocation_uuid = uuid.uuid1()

        workflow_invocation.uuid = invocation_uuid

        workflow_invocation_step1 = model.WorkflowInvocationStep()
        add_object_to_object_session(workflow_invocation_step1, workflow_invocation)
        workflow_invocation_step1.workflow_invocation = workflow_invocation
        workflow_invocation_step1.workflow_step = workflow_step_1

        subworkflow_invocation = model.WorkflowInvocation()
        workflow_invocation.attach_subworkflow_invocation_for_step(workflow_step_2, subworkflow_invocation)

        workflow_invocation_step2 = model.WorkflowInvocationStep()
        add_object_to_object_session(workflow_invocation_step2, workflow_invocation)
        workflow_invocation_step2.workflow_invocation = workflow_invocation
        workflow_invocation_step2.workflow_step = workflow_step_2

        h1 = workflow_invocation.history
        add_object_to_object_session(workflow_invocation, h1)
        d1 = self.new_hda(h1, name="1")
        workflow_request_dataset = model.WorkflowRequestToInputDatasetAssociation()
        add_object_to_object_session(workflow_request_dataset, workflow_invocation)
        workflow_request_dataset.workflow_invocation = workflow_invocation
        workflow_request_dataset.workflow_step = workflow_step_1
        workflow_request_dataset.dataset = d1
        self.persist(workflow_invocation)
        assert workflow_request_dataset is not None
        assert workflow_invocation.id is not None

        history_id = h1.id
        self.expunge()

        loaded_invocation = self.model.session.get(model.WorkflowInvocation, workflow_invocation.id)
        assert loaded_invocation.uuid == invocation_uuid, f"{loaded_invocation.uuid} != {invocation_uuid}"
        assert loaded_invocation
        assert loaded_invocation.history.id == history_id

        # recover user after expunge
        user = loaded_invocation.history.user

        step_1, step_2 = loaded_invocation.workflow.steps

        assert not step_1.subworkflow
        assert step_2.subworkflow
        assert len(loaded_invocation.steps) == 2

        subworkflow_invocation_assoc = loaded_invocation.get_subworkflow_invocation_association_for_step(step_2)
        assert subworkflow_invocation_assoc is not None
        assert isinstance(subworkflow_invocation_assoc.subworkflow_invocation, model.WorkflowInvocation)
        assert isinstance(subworkflow_invocation_assoc.parent_workflow_invocation, model.WorkflowInvocation)

        assert subworkflow_invocation_assoc.subworkflow_invocation.history.id == history_id

        loaded_workflow = self.model.session.get(model.Workflow, workflow_id)
        assert len(loaded_workflow.steps[0].annotations) == 1
        copied_workflow = loaded_workflow.copy(user=user)
        annotations = copied_workflow.steps[0].annotations
        assert len(annotations) == 1

        stored_workflow = loaded_workflow.stored_workflow
        counts = stored_workflow.invocation_counts()
        assert counts

        workflow_invocation_0 = _invocation_for_workflow(user, loaded_workflow)
        workflow_invocation_1 = _invocation_for_workflow(user, loaded_workflow)
        workflow_invocation_1.state = "scheduled"
        self.model.session.add(workflow_invocation_0)
        self.model.session.add(workflow_invocation_1)
        # self.persist(workflow_invocation_0)
        # self.persist(workflow_invocation_1)
        self.model.session.flush()
        counts = stored_workflow.invocation_counts()
        print(counts)
        assert counts.root["new"] == 2
        assert counts.root["scheduled"] == 1

    def test_role_creation(self):
        security_agent = GalaxyRBACAgent(self.model.session)

        def check_private_role(private_role, email):
            assert private_role.type == model.Role.types.PRIVATE
            assert len(private_role.users) == 1
            assert private_role.name == email

        email = "rule_user_1@example.com"
        u = model.User(email=email, password="password")
        self.persist(u)

        role = security_agent.get_private_user_role(u)
        assert role is None
        role = security_agent.create_private_user_role(u)
        assert role is not None
        check_private_role(role, email)

        email = "rule_user_2@example.com"
        u = model.User(email=email, password="password")
        self.persist(u)
        role = security_agent.get_private_user_role(u)
        assert role is None
        role = security_agent.get_private_user_role(u, auto_create=True)
        assert role is not None
        check_private_role(role, email)

        # make sure re-running auto_create doesn't break things
        role = security_agent.get_private_user_role(u, auto_create=True)
        assert role is not None
        check_private_role(role, email)

    def test_private_share_role(self):
        security_agent = GalaxyRBACAgent(self.model.session)

        u_from, u_to, u_other = self._three_users("private_share_role")

        h = model.History(name="History for Annotation", user=u_from)
        d1 = model.HistoryDatasetAssociation(
            extension="txt", history=h, create_dataset=True, sa_session=self.model.session
        )
        self.persist(h, d1)

        security_agent.privately_share_dataset(d1.dataset, [u_to])
        assert security_agent.can_access_dataset(u_to.all_roles(), d1.dataset)
        assert not security_agent.can_access_dataset(u_other.all_roles(), d1.dataset)

    def test_make_dataset_public(self):
        security_agent = GalaxyRBACAgent(self.model.session)
        u_from, u_to, u_other = self._three_users("make_dataset_public")

        h = model.History(name="History for Annotation", user=u_from)
        d1 = model.HistoryDatasetAssociation(
            extension="txt", history=h, create_dataset=True, sa_session=self.model.session
        )
        self.persist(h, d1)

        security_agent.privately_share_dataset(d1.dataset, [u_to])

        security_agent.make_dataset_public(d1.dataset)
        assert security_agent.can_access_dataset(u_to.all_roles(), d1.dataset)
        assert security_agent.can_access_dataset(u_other.all_roles(), d1.dataset)

    def test_set_all_dataset_permissions(self):
        security_agent = GalaxyRBACAgent(self.model.session)
        u_from, _, u_other = self._three_users("set_all_perms")

        h = model.History(name="History for Annotation", user=u_from)
        d1 = model.HistoryDatasetAssociation(
            extension="txt", history=h, create_dataset=True, sa_session=self.model.session
        )
        self.persist(h, d1)

        role = security_agent.get_private_user_role(u_from, auto_create=True)
        access_action = security_agent.permitted_actions.DATASET_ACCESS.action
        manage_action = security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS.action
        permissions = {access_action: [role], manage_action: [role]}
        assert security_agent.can_access_dataset(u_other.all_roles(), d1.dataset)
        security_agent.set_all_dataset_permissions(d1.dataset, permissions)
        assert not security_agent.allow_action(
            u_other.all_roles(), security_agent.permitted_actions.DATASET_ACCESS, d1.dataset
        )
        assert not security_agent.can_access_dataset(u_other.all_roles(), d1.dataset)

    def test_can_manage_privately_shared_dataset(self):
        security_agent = GalaxyRBACAgent(self.model.session)
        u_from, u_to, u_other = self._three_users("can_manage_dataset")

        h = model.History(name="History for Prevent Sharing", user=u_from)
        d1 = model.HistoryDatasetAssociation(
            extension="txt", history=h, create_dataset=True, sa_session=self.model.session
        )
        self.persist(h, d1)

        self._make_owned(security_agent, u_from, d1)
        assert security_agent.can_manage_dataset(u_from.all_roles(), d1.dataset)
        security_agent.privately_share_dataset(d1.dataset, [u_to])
        assert not security_agent.can_manage_dataset(u_to.all_roles(), d1.dataset)

    def test_can_manage_private_dataset(self):
        security_agent = GalaxyRBACAgent(self.model.session)
        u_from, _, u_other = self._three_users("can_manage_dataset_ps")

        h = model.History(name="History for Prevent Sharing", user=u_from)
        d1 = model.HistoryDatasetAssociation(
            extension="txt", history=h, create_dataset=True, sa_session=self.model.session
        )
        self.persist(h, d1)

        self._make_private(security_agent, u_from, d1)
        assert security_agent.can_manage_dataset(u_from.all_roles(), d1.dataset)
        assert not security_agent.can_manage_dataset(u_other.all_roles(), d1.dataset)

    def test_cannot_make_private_objectstore_dataset_public(self):
        security_agent = GalaxyRBACAgent(self.model.session)
        u_from, u_to, _ = self._three_users("cannot_make_private_public")

        h = self.model.History(name="History for Prevent Sharing", user=u_from)
        d1 = self.model.HistoryDatasetAssociation(
            extension="txt", history=h, create_dataset=True, sa_session=self.model.session
        )
        self.persist(h, d1)

        d1.dataset.object_store_id = PRIVATE_OBJECT_STORE_ID
        self._make_private(security_agent, u_from, d1)

        with pytest.raises(Exception) as exec_info:
            self._make_owned(security_agent, u_from, d1)
        assert galaxy.model.CANNOT_SHARE_PRIVATE_DATASET_MESSAGE in str(exec_info.value)

    def test_cannot_make_private_objectstore_dataset_shared(self):
        security_agent = GalaxyRBACAgent(self.model.session)
        u_from, u_to, _ = self._three_users("cannot_make_private_shared")

        h = self.model.History(name="History for Prevent Sharing", user=u_from)
        d1 = self.model.HistoryDatasetAssociation(
            extension="txt", history=h, create_dataset=True, sa_session=self.model.session
        )
        self.persist(h, d1)

        d1.dataset.object_store_id = PRIVATE_OBJECT_STORE_ID
        self._make_private(security_agent, u_from, d1)

        with pytest.raises(Exception) as exec_info:
            security_agent.privately_share_dataset(d1.dataset, [u_to])
        assert galaxy.model.CANNOT_SHARE_PRIVATE_DATASET_MESSAGE in str(exec_info.value)

    def test_cannot_set_dataset_permisson_on_private(self):
        security_agent = GalaxyRBACAgent(self.model.session)
        u_from, u_to, _ = self._three_users("cannot_set_permissions_on_private")

        h = self.model.History(name="History for Prevent Sharing", user=u_from)
        d1 = self.model.HistoryDatasetAssociation(
            extension="txt", history=h, create_dataset=True, sa_session=self.model.session
        )
        self.persist(h, d1)

        d1.dataset.object_store_id = PRIVATE_OBJECT_STORE_ID
        self._make_private(security_agent, u_from, d1)

        role = security_agent.get_private_user_role(u_to, auto_create=True)
        access_action = security_agent.permitted_actions.DATASET_ACCESS.action

        with pytest.raises(Exception) as exec_info:
            security_agent.set_dataset_permission(d1.dataset, {access_action: [role]})
        assert galaxy.model.CANNOT_SHARE_PRIVATE_DATASET_MESSAGE in str(exec_info.value)

    def test_cannot_make_private_dataset_public(self):
        security_agent = GalaxyRBACAgent(self.model.session)
        u_from, u_to, u_other = self._three_users("cannot_make_private_dataset_public")

        h = self.model.History(name="History for Annotation", user=u_from)
        d1 = self.model.HistoryDatasetAssociation(
            extension="txt", history=h, create_dataset=True, sa_session=self.model.session
        )
        self.persist(h, d1)

        d1.dataset.object_store_id = PRIVATE_OBJECT_STORE_ID
        self._make_private(security_agent, u_from, d1)

        with pytest.raises(Exception) as exec_info:
            security_agent.make_dataset_public(d1.dataset)
        assert galaxy.model.CANNOT_SHARE_PRIVATE_DATASET_MESSAGE in str(exec_info.value)

    def _three_users(self, suffix):
        email_from = f"user_{suffix}e1@example.com"
        email_to = f"user_{suffix}e2@example.com"
        email_other = f"user_{suffix}e3@example.com"

        u_from = model.User(email=email_from, password="password")
        u_to = model.User(email=email_to, password="password")
        u_other = model.User(email=email_other, password="password")
        self.persist(u_from, u_to, u_other)
        return u_from, u_to, u_other

    def _make_private(self, security_agent, user, hda):
        role = security_agent.get_private_user_role(user, auto_create=True)
        access_action = security_agent.permitted_actions.DATASET_ACCESS.action
        manage_action = security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS.action
        permissions = {access_action: [role], manage_action: [role]}
        self._set_permissions(security_agent, hda.dataset, permissions)

    def _make_owned(self, security_agent, user, hda):
        role = security_agent.get_private_user_role(user, auto_create=True)
        manage_action = security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS.action
        permissions = {manage_action: [role]}
        self._set_permissions(security_agent, hda.dataset, permissions)

    def _set_permissions(self, security_agent, dataset, permissions):
        # TODO: refactor set_all_dataset_permissions to actually throw an exception :|
        if error := security_agent.set_all_dataset_permissions(dataset, permissions):
            raise Exception(error)

    def new_hda(self, history, **kwds):
        object_store_id = kwds.pop("object_store_id", None)
        hda = self.model.HistoryDatasetAssociation(create_dataset=True, sa_session=self.model.session, **kwds)
        if object_store_id is not None:
            hda.dataset.object_store_id = object_store_id
        return history.add_dataset(hda)


@skip_if_not_postgres_base
class TestPostgresMappings(TestMappings):
    @classmethod
    def _db_uri(cls):
        base = os.environ.get("GALAXY_TEST_UNIT_MAPPING_URI_POSTGRES_BASE")
        dbname = "gxtest" + str(uuid.uuid4())
        assert base
        postgres_url = base + dbname
        create_database(postgres_url)
        return postgres_url


def _invocation_for_workflow(user, workflow):
    h1 = galaxy.model.History(name="WorkflowHistory1", user=user)
    workflow_invocation = galaxy.model.WorkflowInvocation()
    workflow_invocation.workflow = workflow
    workflow_invocation.history = h1
    workflow_invocation.state = "new"
    return workflow_invocation


def _workflow_from_steps(user, steps):
    stored_workflow = galaxy.model.StoredWorkflow()
    add_object_to_object_session(stored_workflow, user)
    stored_workflow.user = user
    workflow = galaxy.model.Workflow()
    if steps:
        for step in steps:
            if get_object_session(step):
                add_object_to_object_session(workflow, step)
                break

    workflow.steps = steps
    workflow.stored_workflow = stored_workflow
    return workflow


class MockObjectStore:
    def __init__(self, quota_source_map=None):
        self._quota_source_map = quota_source_map or QuotaSourceMap()

    def get_quota_source_map(self):
        return self._quota_source_map

    def size(self, dataset):
        return 42

    def exists(self, *args, **kwds):
        return True

    def get_filename(self, *args, **kwds):
        return "mock_dataset_14.dat"

    def construct_path(self, *args, **kwds):
        return "mock_dataset_14.dat"

    def get_store_by(self, *args, **kwds):
        return "id"

    def update_from_file(self, *arg, **kwds):
        pass

    def is_private(self, object):
        if object.object_store_id == PRIVATE_OBJECT_STORE_ID:
            return True
        else:
            return False
