"""
TODO: documentaion on writing model tests goes here

Example:

TestFoo(BaseTest):  # BaseTest is parent class

    # test table-level properties (e.g. table name, indexes, unique constraints)
    def test_table(self, cls_):  # cls_ is fixture defined in parent class, returns class under test.
        assert cls_.__tablename__ == 'foo'  # assert table name
        assert has_index(cls.__table__, ('foo',))  # second arg is a tuple containg field names

    # test column-mapped fields
    def test_columns(self, session, cls_):
        some_foo, some_bar = 42, 'stuff'  # create test values here
        obj = cls_(foo=some_foo)  # pass test values to constructor
        obj.bar = some_bar  # assign test values to obj if can't pass to constructor

        with dbcleanup(session, obj) as obj_id:  # use context manager to ensure obj is deleted from db on exit.
            stored_obj = get_stored_obj(session, cls_, obj_id)  # retrieve data from db and create new obj.
            # check ALL column-mapped fields
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.user_id == user_id
            assert stored_obj.key == key

    # test relationship-mapped fields
    def test_relationships(self, session, cls_):
        obj = cls_()  # use minimal possible constructor

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            # check ALL relationship-mapped fields

# TODO: ADD MORE EXAMPLES!
- point to TestLibraryDataset for example of using more than one object of same type (and, thus,
    not being able to use a fixture.
- TestPage: how to call cleanup explicitly (see average_ratings)
# TODO: explain why we test for columns:
            assert stored_obj.user_id == user_id
            and for relationships:
            assert stored_obj.user.id == user_id
"""

import random
from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest
from sqlalchemy import (
    and_,
    delete,
    select,
    UniqueConstraint,
)

import galaxy.model.mapping as mapping


class BaseTest:
    @pytest.fixture
    def cls_(self, model):
        """
        Return class under test.
        Assumptions: if the class under test is Foo, then the class grouping
        the tests should be a subclass of BaseTest, named TestFoo.
        """
        prefix = len('Test')
        class_name = self.__class__.__name__[prefix:]
        return getattr(model, class_name)


class TestAPIKeys(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'api_keys'

    def test_columns(self, session, cls_, user):
        create_time, user_id, key = datetime.now(), user.id, get_random_string()
        obj = cls_(user_id=user_id, key=key, create_time=create_time)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.user_id == user_id
            assert stored_obj.key == key

    def test_relationships(self, session, cls_, user):
        obj = cls_(user_id=user.id, key=get_random_string())

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.user.id == user.id


class TestCleanupEvent(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'cleanup_event'

    def test_columns(self, session, cls_):
        create_time, message = datetime.now(), 'a'
        obj = cls_(create_time=create_time, message=message)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.message == message


class TestCleanupEventDatasetAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'cleanup_event_dataset_association'

    def test_columns(self, session, cls_, cleanup_event, dataset):
        create_time = datetime.now()
        obj = cls_(create_time=create_time, cleanup_event_id=cleanup_event.id, dataset_id=dataset.id)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.cleanup_event_id == cleanup_event.id
            assert stored_obj.dataset_id == dataset.id


class TestCleanupEventMetadataFileAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'cleanup_event_metadata_file_association'

    def test_columns(self, session, cls_, cleanup_event, metadata_file):
        create_time = datetime.now()
        obj = cls_(create_time=create_time, cleanup_event_id=cleanup_event.id, metadata_file_id=metadata_file.id)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.cleanup_event_id == cleanup_event.id
            assert stored_obj.metadata_file_id == metadata_file.id


class TestCleanupEventHistoryAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == 'cleanup_event_history_association'

    def test_columns(self, session, cls_, cleanup_event, history):
        create_time = datetime.now()
        obj = cls_(create_time=create_time, cleanup_event_id=cleanup_event.id, history_id=history.id)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.cleanup_event_id == cleanup_event.id
            assert stored_obj.history_id == history.id


class TestCleanupEventHistoryDatasetAssociationAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == 'cleanup_event_hda_association'

    def test_columns(self, session, cls_, cleanup_event, history_dataset_association):
        create_time = datetime.now()
        obj = cls_(
            create_time=create_time,
            cleanup_event_id=cleanup_event.id,
            hda_id=history_dataset_association.id
        )

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.cleanup_event_id == cleanup_event.id
            assert stored_obj.hda_id == history_dataset_association.id


class TestCleanupEventLibraryAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == 'cleanup_event_library_association'

    def test_columns(self, session, cls_, cleanup_event, library):
        create_time = datetime.now()
        obj = cls_(create_time=create_time, cleanup_event_id=cleanup_event.id, library_id=library.id)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.cleanup_event_id == cleanup_event.id
            assert stored_obj.library_id == library.id


class TestCleanupEventLibraryFolderAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == 'cleanup_event_library_folder_association'

    def test_columns(self, session, cls_, cleanup_event, library_folder):
        create_time = datetime.now()
        obj = cls_(
            create_time=create_time,
            cleanup_event_id=cleanup_event.id,
            library_folder_id=library_folder.id
        )

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.cleanup_event_id == cleanup_event.id
            assert stored_obj.library_folder_id == library_folder.id


class TestCleanupEventLibraryDatasetAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == 'cleanup_event_library_dataset_association'

    def test_columns(self, session, cls_, cleanup_event, library_dataset):
        create_time = datetime.now()
        obj = cls_(
            create_time=create_time,
            cleanup_event_id=cleanup_event.id,
            library_dataset_id=library_dataset.id
        )

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.cleanup_event_id == cleanup_event.id
            assert stored_obj.library_dataset_id == library_dataset.id


class TestCleanupEventLibraryDatasetDatasetAssociationAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == 'cleanup_event_ldda_association'

    def test_columns(self, session, cls_, cleanup_event, library_dataset_dataset_association):
        create_time = datetime.now()
        obj = cls_(
            create_time=create_time,
            cleanup_event_id=cleanup_event.id,
            ldda_id=library_dataset_dataset_association.id
        )

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.cleanup_event_id == cleanup_event.id
            assert stored_obj.ldda_id == library_dataset_dataset_association.id


class TestCleanupEventImplicitlyConvertedDatasetAssociationAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == 'cleanup_event_icda_association'

    def test_columns(self, session, cls_, cleanup_event, implicitly_converted_dataset_association):
        create_time = datetime.now()
        obj = cls_(
            create_time=create_time,
            cleanup_event_id=cleanup_event.id,
            icda_id=implicitly_converted_dataset_association.id
        )

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.cleanup_event_id == cleanup_event.id
            assert stored_obj.icda_id == implicitly_converted_dataset_association.id


class TestCloudAuthz(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'cloudauthz'

    def test_columns(self, session, cls_, user, user_authnz_token):
        provider, config, description = 'a', 'b', 'c'
        obj = cls_(user.id, provider, config, user_authnz_token.id, description)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.user_id == user.id
            assert stored_obj.provider == provider
            assert stored_obj.config == config
            assert stored_obj.authn_id == user_authnz_token.id
            assert stored_obj.tokens is None
            assert stored_obj.last_update
            assert stored_obj.last_activity
            assert stored_obj.description == description
            assert stored_obj.create_time

    def test_relationships(self, session, cls_, user, user_authnz_token):
        obj = cls_(user.id, None, None, user_authnz_token.id, 'c')

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.user.id == user.id
            assert stored_obj.authn.id == user_authnz_token.id


class TestDataset(BaseTest):

    # def test_table(self, cls_):
    #    assert cls_.__tablename__ == 'dataset'

    def test_columns(self, session, cls_, job):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        state = 'a'
        deleted = True
        purged = True
        purgable = False
        object_store_id = 'b'
        external_filename = 'c'
        _extra_files_path = 'd'
        created_from_basename = 'e'
        file_size = 1
        total_size = 2

        obj = cls_()
        obj.job = job
        obj.create_time = create_time
        obj.update_time = update_time
        obj.state = state
        obj.deleted = deleted
        obj.purged = purged
        obj.purgable = purgable
        obj.object_store_id = object_store_id
        obj.external_filename = external_filename
        obj._extra_files_path = _extra_files_path
        obj.created_from_basename = created_from_basename
        obj.file_size = file_size
        obj.total_size = total_size

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.job_id == job.id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.state == state
            assert stored_obj.deleted == deleted
            assert stored_obj.purged == purged
            assert stored_obj.purgable == purgable
            assert stored_obj.object_store_id == object_store_id
            assert stored_obj.external_filename == external_filename
            assert stored_obj._extra_files_path == _extra_files_path
            assert stored_obj.created_from_basename == created_from_basename
            assert stored_obj.file_size == file_size
            assert stored_obj.total_size == total_size

    def test_relationships(
        self,
        session,
        cls_,
        job,
        dataset_permission,
        history_dataset_association,
        library_dataset_dataset_association,
        dataset_hash,
        dataset_source,
        model,
    ):
        obj = cls_()
        obj.job = job
        obj.actions.append(dataset_permission)
        obj.history_associations.append(history_dataset_association)  # TODO: mappend via backref, map explicitly after HDA is mapped
        obj.library_associations.append(library_dataset_dataset_association)  # TODO: mappend via backref, map explicitly after LDDA is mapped
        obj.hashes.append(dataset_hash)
        obj.sources.append(dataset_source)

        hda = model.HistoryDatasetAssociation()
        hda.purged = True
        obj.history_associations.append(hda)

        with dbcleanup(session, obj) as obj_id, dbcleanup(session, hda):
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id
            assert stored_obj.actions == [dataset_permission]
            assert stored_obj.active_history_associations == [history_dataset_association]
            assert stored_obj.purged_history_associations[0].id == hda.id
            assert stored_obj.active_library_associations == [library_dataset_dataset_association]
            assert stored_obj.hashes == [dataset_hash]
            assert stored_obj.sources == [dataset_source]


class TestDatasetHash(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'dataset_hash'

    def test_columns(self, session, cls_, dataset):
        hash_function, hash_value, extra_files_path = 'a', 'b', 'c'
        obj = cls_()
        obj.dataset = dataset
        obj.hash_function = hash_function
        obj.hash_value = hash_value
        obj.extra_files_path = extra_files_path

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.dataset_id == dataset.id
            assert stored_obj.hash_function == hash_function
            assert stored_obj.hash_value == hash_value
            assert stored_obj.extra_files_path == extra_files_path

    def test_relationships(self, session, cls_, dataset):
        obj = cls_()
        obj.dataset = dataset

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.dataset.id == dataset.id


class TestDatasetSource(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'dataset_source'

    def test_columns(self, session, cls_, dataset, dataset_source_hash):
        source_uri, extra_files_path, transform = 'a', 'b', 'c'
        obj = cls_()
        obj.dataset = dataset
        obj.source_uri = source_uri
        obj.extra_files_path = extra_files_path
        obj.transform = transform

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.dataset_id == dataset.id
            assert stored_obj.source_uri == source_uri
            assert stored_obj.extra_files_path == extra_files_path
            assert stored_obj.transform == transform

    def test_relationships(self, session, cls_, dataset, dataset_source_hash):
        obj = cls_()
        obj.dataset = dataset
        obj.hashes.append(dataset_source_hash)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.dataset.id == dataset.id
            assert stored_obj.hashes == [dataset_source_hash]


class TestDatasetSourceHash(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'dataset_source_hash'

    def test_columns(self, session, cls_, dataset_source):
        hash_function, hash_value = 'a', 'b'
        obj = cls_()
        obj.source = dataset_source
        obj.hash_function = hash_function
        obj.hash_value = hash_value

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.dataset_source_id == dataset_source.id
            assert stored_obj.hash_function == hash_function
            assert stored_obj.hash_value == hash_value

    def test_relationships(self, session, cls_, dataset_source):
        obj = cls_()
        obj.source = dataset_source

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.source.id == dataset_source.id


class TestDatasetPermissions(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'dataset_permissions'

    def test_columns(self, session, cls_, dataset, role):
        action = 'a'
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_(action, dataset, role)
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.update_time == update_time
            assert stored_obj.action == action
            assert stored_obj.dataset_id == dataset.id
            assert stored_obj.role_id == role.id

    def test_relationships(self, session, cls_, dataset, role):
        obj = cls_(None, dataset, role)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.dataset == dataset
            assert stored_obj.role == role


class TestDefaultHistoryPermissions(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'default_history_permissions'

    def test_columns(self, session, cls_, history, role):
        action = 'a'
        obj = cls_(history, action, role)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.action == action
            assert stored_obj.history_id == history.id
            assert stored_obj.role_id == role.id

    def test_relationships(self, session, cls_, history, role):
        obj = cls_(history, None, role)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.history.id == history.id
            assert stored_obj.role == role


class TestDefaultQuotaAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'default_quota_association'

    def test_columns(self, session, cls_, quota):
        type_ = cls_.types.REGISTERED
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_(type_, quota)
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.type == type_
            assert stored_obj.quota_id == quota.id

    def test_relationships(self, session, cls_, quota):
        obj = cls_(cls_.types.REGISTERED, quota)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.quota.id == quota.id


class TestDefaultUserPermissions(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'default_user_permissions'

    def test_columns(self, session, cls_, user, role):
        action = 'a'
        obj = cls_(user, action, role)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.user_id == user.id
            assert stored_obj.action == action
            assert stored_obj.role_id == role.id

    def test_relationships(self, session, cls_, user, role):
        obj = cls_(user, None, role)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.user.id == user.id
            assert stored_obj.role.id == role.id


class TestDeferredJob(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'deferred_job'

    def test_columns(self, session, cls_, model):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        state, plugin, params = model.DeferredJob.states.NEW, 'a', 'b'
        obj = cls_(state, plugin, params)
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.state == state
            assert stored_obj.plugin == plugin
            assert stored_obj.params == params

    def test_relationships(self, session, cls_, genome_index_tool_data):
        obj = cls_()
        obj.deferred_job.append(genome_index_tool_data)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.deferred_job == [genome_index_tool_data]


class TestDynamicTool(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'dynamic_tool'

    def test_columns(self, session, cls_):
        tool_format = 'a'
        tool_id = 'b'
        tool_version = 'c'
        tool_path = 'd'
        tool_directory = 'e'
        uuid = None
        active = True
        hidden = True
        value = 'f'
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_(tool_format, tool_id, tool_version, tool_path, tool_directory, uuid,
                active, hidden, value)
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.uuid
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.tool_id == tool_id
            assert stored_obj.tool_version == tool_version
            assert stored_obj.tool_format == tool_format
            assert stored_obj.tool_path == tool_path
            assert stored_obj.tool_directory == tool_directory
            assert stored_obj.hidden == hidden
            assert stored_obj.active == active
            assert stored_obj.value == value

    def test_relationships(self, session, cls_, workflow_step):
        obj = cls_()
        obj.workflow_steps.append(workflow_step)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.workflow_steps == [workflow_step]


class TestEvent(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'event'

    def test_columns(self, session, cls_, history, galaxy_session, user):
        message, tool_id = 'a', 'b'
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_(message, history, user, galaxy_session)
        obj.create_time = create_time
        obj.update_time = update_time
        obj.tool_id = tool_id

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.history_id == history.id
            assert stored_obj.user_id == user.id
            assert stored_obj.message == message
            assert stored_obj.session_id == galaxy_session.id
            assert stored_obj.tool_id == tool_id

    def test_relationships(self, session, cls_, history, galaxy_session, user):
        obj = cls_(None, history, user, galaxy_session)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.history.id == history.id
            assert stored_obj.user.id == user.id
            assert stored_obj.galaxy_session.id == galaxy_session.id


class TestExtendedMetadata(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'extended_metadata'

    def test_columns(self, session, cls_):
        data = 'a'
        obj = cls_(data)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.data == data

    def test_relationships(self, session, cls_, extended_metadata_index):
        obj = cls_(None)
        obj.children.append(extended_metadata_index)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.children == [extended_metadata_index]


class TestExtendedMetadataIndex(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'extended_metadata_index'

    def test_columns(self, session, cls_, extended_metadata):
        path, value = 'a', 'b'
        obj = cls_(extended_metadata, path, value)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.extended_metadata_id == extended_metadata.id
            assert stored_obj.path == path
            assert stored_obj.value == value

    def test_relationships(self, session, cls_, extended_metadata):
        obj = cls_(extended_metadata, None, None)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.extended_metadata.id == extended_metadata.id


class TestFormDefinition(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'form_definition'

    def test_columns(self, session, cls_, form_definition_current):
        name, desc, fields, type, layout = 'a', 'b', 'c', 'd', 'e'
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_()
        obj.name = name
        obj.desc = desc
        obj.form_definition_current = form_definition_current
        obj.fields = fields
        obj.type = type
        obj.layout = layout
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.name == name
            assert stored_obj.desc == desc
            assert stored_obj.form_definition_current_id == form_definition_current.id
            assert stored_obj.fields == fields
            assert stored_obj.type == type
            assert stored_obj.layout == layout

    def test_relationships(self, session, cls_, form_definition_current):
        obj = cls_(name='a', form_definition_current=form_definition_current)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.form_definition_current.id == form_definition_current.id


class TestFormDefinitionCurrent(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'form_definition_current'

    def test_columns(self, session, cls_, form_definition):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        deleted = True
        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.latest_form = form_definition
        obj.deleted = deleted

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.latest_form_id == form_definition.id
            assert stored_obj.deleted == deleted

    def test_relationships(self, session, cls_, form_definition):
        obj = cls_(form_definition)
        obj.forms.append(form_definition)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.latest_form.id == form_definition.id
            assert stored_obj.forms == [form_definition]


class TestFormValues(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'form_values'

    def test_columns(self, session, cls_, form_definition):
        content = 'a'
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_()
        obj.form_definition = form_definition
        obj.content = content
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.content == content
            assert stored_obj.form_definition_id == form_definition.id

    def test_relationships(self, session, cls_, form_definition):
        obj = cls_(form_definition)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.form_definition.id == form_definition.id


class TestGalaxySession(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'galaxy_session'

    def test_columns(self, session, cls_, user, history, galaxy_session):

        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        remote_host = 'a'
        remote_addr = 'b'
        referer = 'c'
        session_key = 'd'
        is_valid = True
        disk_usage = 9
        last_action = update_time + timedelta(hours=1)

        obj = cls_(user=user, current_history=history, prev_session_id=galaxy_session.id)

        obj.create_time = create_time
        obj.update_time = update_time
        obj.remote_host = remote_host
        obj.remote_addr = remote_addr
        obj.referer = referer
        obj.session_key = session_key
        obj.is_valid = is_valid
        obj.disk_usage = disk_usage
        obj.last_action = last_action

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.user_id == user.id
            assert stored_obj.remote_host == remote_host
            assert stored_obj.remote_addr == remote_addr
            assert stored_obj.referer == referer
            assert stored_obj.current_history_id == history.id
            assert stored_obj.session_key == session_key
            assert stored_obj.is_valid == is_valid
            assert stored_obj.prev_session_id == galaxy_session.id
            assert stored_obj.disk_usage == disk_usage
            assert stored_obj.last_action == last_action

    def test_relationships(self, session, cls_, user, history, galaxy_session_history_association):
        obj = cls_(user=user, current_history=history)
        obj.histories.append(galaxy_session_history_association)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.user.id == user.id
            assert stored_obj.current_history.id == history.id
            assert stored_obj.histories == [galaxy_session_history_association]


class TestGalaxySessionToHistoryAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'galaxy_session_to_history'

    def test_columns(self, session, cls_, galaxy_session, history):
        create_time = datetime.now()
        obj = cls_(galaxy_session, history)
        obj.create_time = create_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.session_id == galaxy_session.id
            assert stored_obj.history_id == history.id

    def test_relationships(self, session, cls_, galaxy_session, history):
        obj = cls_(galaxy_session, history)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.galaxy_session.id == galaxy_session.id
            assert stored_obj.history.id == history.id


class TestGenomeIndexToolData(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'genome_index_tool_data'

    def test_columns(self, session, cls_, job, deferred_job, transfer_job, dataset, user):
        fasta_path = 'a'
        created_time = datetime.now()
        modified_time = created_time + timedelta(hours=1)
        indexer = 'b'
        obj = cls_()
        obj.job = job
        obj.deferred = deferred_job
        obj.transfer = transfer_job
        obj.dataset = dataset
        obj.fasta_path = fasta_path
        obj.created_time = created_time
        obj.modified_time = modified_time
        obj.indexer = indexer
        obj.user = user

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.job_id == job.id
            assert stored_obj.deferred_job_id == deferred_job.id
            assert stored_obj.transfer_job_id == transfer_job.id
            assert stored_obj.dataset_id == dataset.id
            assert stored_obj.fasta_path == fasta_path
            assert stored_obj.created_time == created_time
            assert stored_obj.modified_time == modified_time
            assert stored_obj.indexer == indexer
            assert stored_obj.user_id == user.id

    def test_relationships(self, session, cls_, job, deferred_job, transfer_job, dataset, user):
        obj = cls_()
        obj.job = job
        obj.deferred = deferred_job
        obj.transfer = transfer_job
        obj.dataset = dataset
        obj.user = user

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id
            assert stored_obj.deferred.id == deferred_job.id
            assert stored_obj.transfer.id == transfer_job.id
            assert stored_obj.dataset.id == dataset.id
            assert stored_obj.user.id == user.id


class TestGroupQuotaAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'group_quota_association'

    def test_columns(self, session, cls_, group, quota):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_(group, quota)
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.group_id == group.id
            assert stored_obj.quota_id == quota.id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time

    def test_relationships(self, session, cls_, group, quota):
        obj = cls_(group, quota)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.group.id == group.id
            assert stored_obj.quota.id == quota.id


class TestGroupRoleAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'group_role_association'

    def test_columns(self, session, cls_, group, role):
        obj = cls_(group, role)
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.group_id == group.id
            assert stored_obj.role_id == role.id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time

    def test_relationships(self, session, cls_, group, role):
        obj = cls_(group, role)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.group.id == group.id
            assert stored_obj.role.id == role.id


class TestHistory(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'history'
        assert has_index(cls_.__table__, ('slug',))

    def test_columns(self, session, cls_, user):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        name = 'a'
        hid_counter = 2
        deleted = True
        purged = True
        importing = True
        genome_build = 'b'
        importable = True
        slug = 'c'
        published = True
        obj = cls_(name=name, user=user)
        obj.create_time = create_time
        obj.update_time = update_time
        obj.hid_counter = hid_counter
        obj.deleted = deleted
        obj.purged = purged
        obj.importing = importing
        obj.genome_build = genome_build
        obj.importable = importable
        obj.slug = slug
        obj.published = published

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            # cannot test directly (trigger); applies to both column and column property
            assert stored_obj.update_time
            assert stored_obj.user_id == user.id
            assert stored_obj.name == name
            assert stored_obj.hid_counter == hid_counter
            assert stored_obj.deleted == deleted
            assert stored_obj.purged == purged
            assert stored_obj.importing == importing
            assert stored_obj.genome_build == genome_build
            assert stored_obj.importable == importable
            assert stored_obj.slug == slug
            assert stored_obj.published == published

    def test_relationships(
        self,
        session,
        cls_,
        user,
        history_dataset_association,
        job_export_history_archive,
        history_dataset_collection_association,
        history_tag_association,
        history_annotation_association,
        history_rating_association,
        default_history_permissions,
        history_user_share_association,
        galaxy_session_history_association,
        model,
    ):
        obj = cls_()
        obj.user = user
        obj.datasets.append(history_dataset_association)

        # TODO: this is mappend via backref: change to back_populates after mapping HDCA
        obj.dataset_collections.append(history_dataset_collection_association)

        obj.exports.append(job_export_history_archive)
        obj.tags.append(history_tag_association)
        obj.annotations.append(history_annotation_association)
        obj.ratings.append(history_rating_association)
        obj.default_permissions.append(default_history_permissions)
        obj.users_shared_with.append(history_user_share_association)
        obj.galaxy_sessions.append(galaxy_session_history_association)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.user.id == user.id
            assert stored_obj.datasets == [history_dataset_association]
            assert stored_obj.exports == [job_export_history_archive]
            assert stored_obj.active_datasets == [history_dataset_association]
            assert stored_obj.active_dataset_collections == [history_dataset_collection_association]
            assert stored_obj.visible_datasets == [history_dataset_association]
            assert stored_obj.visible_dataset_collections == [history_dataset_collection_association]
            assert stored_obj.tags == [history_tag_association]
            assert stored_obj.annotations == [history_annotation_association]
            assert stored_obj.ratings == [history_rating_association]
            # This doesn't test the average amount, just the mapping.
            assert stored_obj.average_rating == history_rating_association.rating
            assert stored_obj.users_shared_with_count == 1
            assert stored_obj.users_shared_with == [history_user_share_association]
            assert stored_obj.default_permissions == [default_history_permissions]
            assert stored_obj.galaxy_sessions == [galaxy_session_history_association]

    def test_average_rating(self, model, session, history, user):
        # History has been expunged; to access its deferred properties,
        # it needs to be added back to the session.
        session.add(history)
        assert history.average_rating is None  # With no ratings, we expect None.
        # Create ratings
        to_cleanup = []
        for rating in (1, 2, 3, 4, 5):
            history_rating_assoc = model.HistoryRatingAssociation(user, history)
            history_rating_assoc.rating = rating
            persist(session, history_rating_assoc)
            to_cleanup.append(history_rating_assoc)
        assert history.average_rating == 3.0  # Expect average after ratings added.
        # Cleanup: remove ratings from database
        delete_from_database(session, to_cleanup)


class TestHistoryDatasetAssociationHistory(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'history_dataset_association_history'

    def test_columns(self, session, cls_, history_dataset_association, extended_metadata):
        name, update_time, version, extension, metadata = 'a', datetime.now(), 2, 'b', 'c'
        obj = cls_(
            history_dataset_association.id,
            name,
            None,
            update_time,
            version,
            extension,
            extended_metadata.id,
            metadata
        )

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.history_dataset_association_id == history_dataset_association.id
            assert stored_obj.name == name
            assert stored_obj.update_time == update_time
            assert stored_obj.version == version
            assert stored_obj.extension == extension
            assert stored_obj.extended_metadata_id == extended_metadata.id
            assert stored_obj._metadata == metadata


class TestHistoryUserShareAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'history_user_share_association'

    def test_columns(self, session, cls_, history, user):
        obj = cls_()
        obj.history = history
        obj.user = user

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.history_id == history.id
            assert stored_obj.user_id == user.id

    def test_relationships(self, session, cls_, history, user):
        obj = cls_()
        obj.history = history
        obj.user = user

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.history.id == history.id
            assert stored_obj.user.id == user.id


class TestHistoryAudit(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'history_audit'

    def test_columns_and_relationships(self, session, cls_, history):
        update_time = datetime.now()
        obj = cls_(history, update_time)

        where_clause = and_(cls_.history_id == history.id, cls_.update_time == update_time)

        with dbcleanup(session, obj, where_clause):
            stored_obj = get_stored_obj(session, cls_, where_clause=where_clause)
            # test columns
            assert stored_obj.history_id == history.id
            assert stored_obj.update_time == update_time
            # test relationships
            assert stored_obj.history.id == history.id


class TestHistoryAnnotationAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'history_annotation_association'
        assert has_index(cls_.__table__, ('annotation',))

    def test_columns(self, session, cls_, history, user):
        annotation = 'a'
        obj = cls_()
        obj.user = user
        obj.history = history
        obj.annotation = annotation

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.history_id == history.id
            assert stored_obj.user_id == user.id
            assert stored_obj.annotation == annotation

    def test_relationships(self, session, cls_, history, user):
        obj = cls_()
        obj.user = user
        obj.history = history

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.history.id == history.id
            assert stored_obj.user.id == user.id


class TestHistoryDatasetAssociationAnnotationAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'history_dataset_association_annotation_association'
        assert has_index(cls_.__table__, ('annotation',))

    def test_columns(self, session, cls_, history_dataset_association, user):
        annotation = 'a'
        obj = cls_()
        obj.user = user
        obj.hda = history_dataset_association
        obj.annotation = annotation

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.history_dataset_association_id == history_dataset_association.id
            assert stored_obj.user_id == user.id
            assert stored_obj.annotation == annotation

    def test_relationships(self, session, cls_, history_dataset_association, user):
        obj = cls_()
        obj.user = user
        obj.hda = history_dataset_association

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.hda.id == history_dataset_association.id
            assert stored_obj.user.id == user.id


class TestHistoryDatasetAssociationDisplayAtAuthorization(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'history_dataset_association_display_at_authorization'

    def test_columns(self, session, cls_, history_dataset_association, user):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        site = 'a'
        obj = cls_(history_dataset_association, user, site)
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.history_dataset_association_id == history_dataset_association.id
            assert stored_obj.user_id == user.id
            assert stored_obj.site == site

    def test_relationships(self, session, cls_, history_dataset_association, user):
        obj = cls_(history_dataset_association, user)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.history_dataset_association.id == history_dataset_association.id
            assert stored_obj.user.id == user.id


class TestHistoryDatasetAssociationRatingAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'history_dataset_association_rating_association'

    def test_columns(self, session, cls_, history_dataset_association, user):
        rating = 9
        obj = cls_(user, history_dataset_association, rating)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.user_id == user.id
            assert stored_obj.rating == rating

    def test_relationships(self, session, cls_, history_dataset_association, user):
        obj = cls_(user, history_dataset_association, 1)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.history_dataset_association.id == history_dataset_association.id
            assert stored_obj.user.id == user.id


class TestHistoryDatasetAssociationTagAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'history_dataset_association_tag_association'

    def test_columns(self, session, cls_, history_dataset_association, tag, user):
        user_tname, value, user_value = 'a', 'b', 'c'
        obj = cls_(user=user, tag=tag, user_tname=user_tname, value=value, user_value=user_value)
        obj.history_dataset_association = history_dataset_association

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.history_dataset_association_id == history_dataset_association.id
            assert stored_obj.tag_id == tag.id
            assert stored_obj.user_id == user.id
            assert stored_obj.user_tname == user_tname
            assert stored_obj.value == value
            assert stored_obj.user_value == user_value

    def test_relationships(self, session, cls_, history_dataset_association, tag, user):
        obj = cls_(user=user, tag=tag)
        obj.history_dataset_association = history_dataset_association

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.history_dataset_association.id == history_dataset_association.id
            assert stored_obj.tag.id == tag.id
            assert stored_obj.user.id == user.id


class TestHistoryDatasetCollectionAssociationAnnotationAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'history_dataset_collection_annotation_association'

    def test_columns(self, session, cls_, history_dataset_collection_association, user):
        annotation = 'a'
        obj = cls_()
        obj.user = user
        obj.history_dataset_collection = history_dataset_collection_association
        obj.annotation = annotation

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.history_dataset_collection_id == history_dataset_collection_association.id
            assert stored_obj.user_id == user.id
            assert stored_obj.annotation == annotation

    def test_relationships(self, session, cls_, history_dataset_collection_association, user):
        obj = cls_()
        obj.user = user
        obj.history_dataset_collection = history_dataset_collection_association

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.history_dataset_collection.id == history_dataset_collection_association.id
            assert stored_obj.user.id == user.id


class TestHistoryDatasetCollectionRatingAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'history_dataset_collection_rating_association'

    def test_columns(self, session, cls_, history_dataset_collection_association, user):
        rating = 9
        obj = cls_(user, history_dataset_collection_association, rating)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.history_dataset_collection_id == history_dataset_collection_association.id
            assert stored_obj.user.id == user.id
            assert stored_obj.rating == rating

    def test_relationships(self, session, cls_, history_dataset_collection_association, user):
        obj = cls_(user, history_dataset_collection_association, 1)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.dataset_collection.id == history_dataset_collection_association.id
            assert stored_obj.user.id == user.id


class TestHistoryDatasetCollectionTagAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'history_dataset_collection_tag_association'

    def test_columns(self, session, cls_, history_dataset_collection_association, tag, user):
        user_tname, value, user_value = 'a', 'b', 'c'
        obj = cls_(user=user, tag=tag, user_tname=user_tname, value=value, user_value=user_value)
        obj.dataset_collection = history_dataset_collection_association

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.history_dataset_collection_id == history_dataset_collection_association.id
            assert stored_obj.tag_id == tag.id
            assert stored_obj.user_id == user.id
            assert stored_obj.user_tname == user_tname
            assert stored_obj.value == value
            assert stored_obj.user_value == user_value

    def test_relationships(self, session, cls_, history_dataset_collection_association, tag, user):
        obj = cls_(user=user, tag=tag)
        obj.dataset_collection = history_dataset_collection_association

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.dataset_collection.id == history_dataset_collection_association.id
            assert stored_obj.tag.id == tag.id
            assert stored_obj.user.id == user.id


class TestHistoryRatingAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'history_rating_association'

    def test_columns(self, session, cls_, history, user):
        rating = 9
        obj = cls_(user, history, rating)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.history_id == history.id
            assert stored_obj.user_id == user.id
            assert stored_obj.rating == rating

    def test_relationships(self, session, cls_, history, user):
        obj = cls_(user, history, 1)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.history.id == history.id
            assert stored_obj.user.id == user.id


class TestHistoryTagAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'history_tag_association'

    def test_columns(self, session, cls_, history, tag, user):
        user_tname, value, user_value = 'a', 'b', 'c'
        obj = cls_(user=user, tag=tag, user_tname=user_tname, value=value)
        obj.user_value = user_value
        obj.history = history

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.history_id == history.id
            assert stored_obj.tag_id == tag.id
            assert stored_obj.user_id == user.id
            assert stored_obj.user_tname == user_tname
            assert stored_obj.value == value
            assert stored_obj.user_value == user_value

    def test_relationships(self, session, cls_, history, tag, user):
        obj = cls_(user=user, tag=tag)
        obj.history = history

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.history.id == history.id
            assert stored_obj.tag.id == tag.id
            assert stored_obj.user.id == user.id


class TestImplicitCollectionJobs(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'implicit_collection_jobs'

    def test_columns(self, session, cls_, model):
        populated_state = model.ImplicitCollectionJobs.populated_states.NEW
        obj = cls_()
        obj.populated_state = populated_state

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.populated_state == populated_state

    def test_relationships(self, session, cls_, implicit_collection_jobs_job_association):
        obj = cls_()
        obj.jobs.append(implicit_collection_jobs_job_association)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.jobs == [implicit_collection_jobs_job_association]


class TestImplicitCollectionJobsJobAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'implicit_collection_jobs_job_association'

    def test_columns(self, session, cls_, implicit_collection_jobs, job):
        order_index = 1
        obj = cls_()
        obj.implicit_collection_jobs = implicit_collection_jobs
        session.add(job)  # TODO review this after remapping Job (required to lazy-load attr)
        obj.job = job
        obj.order_index = order_index

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.implicit_collection_jobs_id == implicit_collection_jobs.id
            assert stored_obj.job_id == job.id
            assert stored_obj.order_index == order_index

    def test_relationships(self, session, cls_, implicit_collection_jobs, job):
        obj = cls_()
        obj.implicit_collection_jobs = implicit_collection_jobs
        session.add(job)  # TODO review this after remapping Job (required to lazy-load attr)
        obj.job = job
        obj.order_index = 1

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.implicit_collection_jobs.id == implicit_collection_jobs.id
            assert stored_obj.job.id == job.id


class TestImplicitlyCreatedDatasetCollectionInput(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'implicitly_created_dataset_collection_inputs'

    def test_columns(self, session, cls_, history_dataset_collection_association, model):
        name = 'a'

        hdca2 = model.HistoryDatasetCollectionAssociation()
        persist(session, hdca2)

        obj = cls_(name, history_dataset_collection_association)
        obj.dataset_collection_id = hdca2.id

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.input_dataset_collection_id == history_dataset_collection_association.id
            assert stored_obj.dataset_collection_id == hdca2.id
            assert stored_obj.name == name

        delete_from_database(session, [hdca2])

    def test_relationships(self, session, cls_, history_dataset_collection_association, model):
        hdca2 = model.HistoryDatasetCollectionAssociation()
        persist(session, hdca2)

        obj = cls_(None, history_dataset_collection_association)
        obj.dataset_collection_id = hdca2.id

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.input_dataset_collection.id == history_dataset_collection_association.id
            assert stored_obj.dataset_collection.id == hdca2.id

        delete_from_database(session, [hdca2])


class TestInteractiveToolEntryPoint(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'interactivetool_entry_point'

    def test_columns(self, session, cls_, job):
        name = 'a'
        token = 'b'
        tool_port = 1
        host = 'c'
        port = 2
        protocol = 'd'
        entry_url = 'e'
        requires_domain = False
        info = 'f'
        configured = True
        deleted = True
        created_time = datetime.now()
        modified_time = created_time + timedelta(hours=1)

        obj = cls_()

        obj.job = job
        obj.name = name
        obj.token = token
        obj.tool_port = tool_port
        obj.host = host
        obj.port = port
        obj.protocol = protocol
        obj.entry_url = entry_url
        obj.requires_domain = requires_domain
        obj.info = info
        obj.configured = configured
        obj.deleted = deleted
        obj.created_time = created_time
        obj.modified_time = modified_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.job_id == job.id
            assert stored_obj.name == name
            assert stored_obj.token == token
            assert stored_obj.tool_port == tool_port
            assert stored_obj.host == host
            assert stored_obj.port == port
            assert stored_obj.protocol == protocol
            assert stored_obj.entry_url == entry_url
            assert stored_obj.requires_domain == requires_domain
            assert stored_obj.info == info
            assert stored_obj.configured == configured
            assert stored_obj.deleted == deleted
            assert stored_obj.created_time == created_time
            assert stored_obj.modified_time == modified_time

    def test_relationships(self, session, cls_, job):
        obj = cls_(job=job)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id


class TestJobContainerAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'job_container_association'

    def test_columns(self, session, cls_, job):
        container_type = 'a'
        container_name = 'b'
        container_info = 'c'
        created_time = datetime.now()
        modified_time = created_time + timedelta(hours=1)

        session.add(job)  # TODO review this after remapping Job (required to lazy-load `container` attr)

        obj = cls_(job, container_type, container_name, container_info)
        obj.created_time = created_time
        obj.modified_time = modified_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.job_id == job.id
            assert stored_obj.container_type == container_type
            assert stored_obj.container_name == container_name
            assert stored_obj.container_info == container_info
            assert stored_obj.created_time == created_time
            assert stored_obj.modified_time == modified_time

    def test_relationships(self, session, cls_, job):
        session.add(job)  # TODO review this after remapping Job (required to lazy-load `container` attr)
        obj = cls_(job, None, None, None)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id


class TestJobExportHistoryArchive(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'job_export_history_archive'

    def test_columns(self, session, cls_, job, history, dataset):
        compressed, history_attrs_filename = True, 'a'
        obj = cls_(job, history, dataset, compressed, history_attrs_filename)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.job_id == job.id
            assert stored_obj.history_id == history.id
            assert stored_obj.dataset_id == dataset.id
            assert stored_obj.compressed == compressed
            assert stored_obj.history_attrs_filename == history_attrs_filename

    def test_relationships(self, session, cls_, job, history, dataset):
        obj = cls_(job, history, dataset, True, None)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id
            assert stored_obj.history.id == history.id
            assert stored_obj.dataset.id == dataset.id


class TestJobExternalOutputMetadata(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'job_external_output_metadata'

    def test_columns(
        self,
        session,
        cls_,
        job,
        history_dataset_association,
        library_dataset_dataset_association
    ):
        is_valid = False
        filename_in = 'a'
        filename_out = 'b'
        filename_results_code = 'c'
        filename_kwds = 'd'
        filename_override_metadata = 'e'
        job_runner_external_pid = 'f'

        # We can only pass one dataset: an hda or a ldda, but we need to test both.
        # First test passing an hda
        obj = cls_(job, history_dataset_association)

        obj.is_valid = is_valid
        obj.filename_in = filename_in
        obj.filename_out = filename_out
        obj.filename_results_code = filename_results_code
        obj.filename_kwds = filename_kwds
        obj.filename_override_metadata = filename_override_metadata
        obj.job_runner_external_pid = job_runner_external_pid

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.job_id == job.id
            assert stored_obj.history_dataset_association_id == history_dataset_association.id
            assert stored_obj.is_valid == is_valid
            assert stored_obj.filename_in == filename_in
            assert stored_obj.filename_out == filename_out
            assert stored_obj.filename_results_code == filename_results_code
            assert stored_obj.filename_kwds == filename_kwds
            assert stored_obj.filename_override_metadata == filename_override_metadata
            assert stored_obj.job_runner_external_pid == job_runner_external_pid

        # Now pass an ldda (w/no extra fields, since we've just tested them)
        obj = cls_(job, library_dataset_dataset_association)
        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.library_dataset_dataset_association_id == library_dataset_dataset_association.id

    def test_relationships(
        self,
        session,
        cls_,
        job,
        history_dataset_association,
        library_dataset_dataset_association
    ):
        # First test passing an hda
        obj = cls_(job, history_dataset_association)
        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id
            assert stored_obj.dataset.id == history_dataset_association.id

        # Now pass an ldda
        obj = cls_(job, library_dataset_dataset_association)
        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.dataset.id == library_dataset_dataset_association.id


class TestJobImportHistoryArchive(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'job_import_history_archive'

    def test_columns(self, session, cls_, job, history):
        archive_dir = 'a'
        obj = cls_(job, history, archive_dir)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.job_id == job.id
            assert stored_obj.history_id == history.id
            assert stored_obj. archive_dir == archive_dir

    def test_relationships(self, session, cls_, job, history, dataset):
        obj = cls_(job, history)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id
            assert stored_obj.history.id == history.id


class TestJobMetricNumeric(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'job_metric_numeric'

    def test_columns(self, session, cls_, job):
        plugin, metric_name, metric_value = 'a', 'b', 9
        obj = cls_(plugin, metric_name, metric_value)
        obj.job = job

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.job_id == job.id
            assert stored_obj.plugin == plugin
            assert stored_obj.metric_value == metric_value

    def test_relationships(self, session, cls_, job):
        obj = cls_(None, None, None)
        obj.job = job

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id


class TestJobMetricText(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'job_metric_text'

    def test_columns(self, session, cls_, job):
        plugin, metric_name, metric_value = 'a', 'b', 'c'
        obj = cls_(plugin, metric_name, metric_value)
        obj.job = job

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.job_id == job.id
            assert stored_obj.plugin == plugin
            assert stored_obj.metric_value == metric_value

    def test_relationships(self, session, cls_, job):
        obj = cls_(None, None, None)
        obj.job = job

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id


class TestJobParameter(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'job_parameter'

    def test_columns(self, session, cls_, job):
        name, value = 'a', 'b'
        obj = cls_(name, value)
        obj.job_id = job.id

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.job_id == job.id
            assert stored_obj.name == name
            assert stored_obj.value == value


class TestJobStateHistory(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'job_state_history'

    def test_columns(self, session, cls_, job):
        state, info = job.state, job.info
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_(job)
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.job_id == job.id
            assert stored_obj.state == state
            assert stored_obj.info == info

    def test_relationships(self, session, cls_, job):
        obj = cls_(job)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id


class TestJobToImplicitOutputDatasetCollectionAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'job_to_implicit_output_dataset_collection'

    def test_columns(self, session, cls_, dataset_collection, job):
        name = 'a'
        obj = cls_(name, dataset_collection)
        obj.job = job

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.job_id == job.id
            assert stored_obj.dataset_collection_id == dataset_collection.id
            assert stored_obj.name == name

    def test_relationships(self, session, cls_, dataset_collection, job):
        obj = cls_(None, dataset_collection)
        obj.job = job

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id
            assert stored_obj.dataset_collection.id == dataset_collection.id


class TestJobToInputDatasetCollectionAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'job_to_input_dataset_collection'

    def test_columns(self, session, cls_, history_dataset_collection_association, job):
        name = 'a'
        obj = cls_(name, history_dataset_collection_association)
        obj.job = job

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.job_id == job.id
            assert stored_obj.dataset_collection_id == history_dataset_collection_association.id
            assert stored_obj.name == name

    def test_relationships(self, session, cls_, history_dataset_collection_association, job):
        obj = cls_(None, history_dataset_collection_association)
        obj.job = job

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id
            assert stored_obj.dataset_collection.id == history_dataset_collection_association.id


class TestJobToInputDatasetCollectionElementAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'job_to_input_dataset_collection_element'

    def test_columns(self, session, cls_, dataset_collection_element, job):
        name = 'a'
        obj = cls_(name, dataset_collection_element)
        obj.job = job

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.job_id == job.id
            assert stored_obj.dataset_collection_element_id == dataset_collection_element.id
            assert stored_obj.name == name

    def test_relationships(self, session, cls_, dataset_collection_element, job):
        obj = cls_(None, dataset_collection_element)
        obj.job = job

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id
            assert stored_obj.dataset_collection_element.id == dataset_collection_element.id


class TestJobToInputDatasetAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'job_to_input_dataset'

    def test_columns(self, session, cls_, history_dataset_association, job):
        name, dataset_version = 'a', 9
        obj = cls_(name, history_dataset_association)
        obj.job = job
        obj.dataset_version = dataset_version

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.job_id == job.id
            assert stored_obj.dataset_id == history_dataset_association.id
            assert stored_obj.dataset_version == dataset_version
            assert stored_obj.name == name

    def test_relationships(self, session, cls_, history_dataset_association, job):
        obj = cls_(None, history_dataset_association)
        obj.job = job

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id
            assert stored_obj.dataset.id == history_dataset_association.id


class TestJobToInputLibraryDatasetAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'job_to_input_library_dataset'

    def test_columns(self, session, cls_, library_dataset_dataset_association, job):
        name = 'a'
        obj = cls_(name, library_dataset_dataset_association)
        obj.job = job

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.job_id == job.id
            assert stored_obj.ldda_id == library_dataset_dataset_association.id
            assert stored_obj.name == name

    def test_relationships(self, session, cls_, library_dataset_dataset_association, job):
        obj = cls_(None, library_dataset_dataset_association)
        obj.job = job

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id
            assert stored_obj.dataset.id == library_dataset_dataset_association.id


class TestJobToOutputDatasetAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'job_to_output_dataset'

    def test_columns(self, session, cls_, history_dataset_association, job):
        name = 'a'
        obj = cls_(name, history_dataset_association)
        obj.job = job

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.job_id == job.id
            assert stored_obj.dataset_id == history_dataset_association.id
            assert stored_obj.name == name

    def test_relationships(self, session, cls_, history_dataset_association, job):
        obj = cls_(None, history_dataset_association)
        obj.job = job

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id
            assert stored_obj.dataset.id == history_dataset_association.id


class TestJobToOutputDatasetCollectionAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'job_to_output_dataset_collection'

    def test_columns(self, session, cls_, history_dataset_collection_association, job):
        name = 'a'
        obj = cls_(name, history_dataset_collection_association)
        obj.job = job

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.job_id == job.id
            assert stored_obj.dataset_collection_id == history_dataset_collection_association.id
            assert stored_obj.name == name

    def test_relationships(self, session, cls_, history_dataset_collection_association, job):
        obj = cls_(None, history_dataset_collection_association)
        obj.job = job

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id
            assert stored_obj.dataset_collection_instance.id == history_dataset_collection_association.id


class TestLibraryDataset(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'library_dataset'

    def test_columns(self, session, cls_, library_dataset_dataset_association, library_folder):
        order_id = 9
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        name = 'a'
        info = 'b'
        deleted = False
        purged = False

        obj = cls_()
        obj.folder = library_folder
        obj.order_id = order_id
        obj.create_time = create_time
        obj.update_time = update_time
        obj.name = name
        obj.info = info
        obj.deleted = deleted
        obj.purged = purged

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.folder_id == library_folder.id
            assert stored_obj.order_id == order_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.name == name
            assert stored_obj.info == info
            assert stored_obj.deleted == deleted
            assert stored_obj.purged == purged

    def test_relationships(
        self,
        session,
        cls_,
        library_dataset_dataset_association,
        library_folder,
        library_dataset_permission,
        model,
    ):
        obj = cls_()
        obj.folder = library_folder
        obj.library_dataset_dataset_association = library_dataset_dataset_association
        obj.actions.append(library_dataset_permission)

        ldda = model.LibraryDatasetDatasetAssociation()
        ldda.library_dataset = obj
        obj.actions.append(library_dataset_permission)

        with dbcleanup(session, obj) as obj_id, dbcleanup(session, ldda):
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.library_dataset_dataset_association.id == library_dataset_dataset_association.id
            assert stored_obj.folder.id == library_folder.id
            assert stored_obj.expired_datasets[0].id == ldda.id
            assert stored_obj.actions == [library_dataset_permission]


class TestJobToOutputLibraryDatasetAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'job_to_output_library_dataset'

    def test_columns(self, session, cls_, library_dataset_dataset_association, job):
        name = 'a'
        obj = cls_(name, library_dataset_dataset_association)
        obj.job = job

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.job_id == job.id
            assert stored_obj.ldda_id == library_dataset_dataset_association.id
            assert stored_obj.name == name

    def test_relationships(self, session, cls_, library_dataset_dataset_association, job):
        obj = cls_(None, library_dataset_dataset_association)
        obj.job = job

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id
            assert stored_obj.dataset.id == library_dataset_dataset_association.id


class TestLibrary(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'library'

    def test_columns(self, session, cls_, library_folder):
        name, deleted, purged, description, synopsis = 'a', True, True, 'b', 'c'
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_(name, description, synopsis, library_folder)
        obj.create_time = create_time
        obj.update_time = update_time
        obj.deleted = deleted
        obj.purged = purged

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.root_folder_id == library_folder.id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.name == name
            assert stored_obj.deleted == deleted
            assert stored_obj.purged == purged
            assert stored_obj.description == description
            assert stored_obj.synopsis == synopsis

    def test_relationships(
        self,
        session,
        cls_,
        library_folder,
        library_permission,
        library_info_association,
    ):
        obj = cls_(None, None, None, library_folder)
        obj.actions.append(library_permission)
        session.add(library_info_association)  # must be bound to a session for lazy load of attr. `library` (https://docs.sqlalchemy.org/en/14/errors.html#error-bhk3)
        obj.info_association.append(library_info_association)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.root_folder.id == library_folder.id
            assert stored_obj.actions == [library_permission]
            assert stored_obj.info_association == [library_info_association]


class TestLibraryDatasetCollectionAnnotationAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'library_dataset_collection_annotation_association'

    def test_columns(self, session, cls_, library_dataset_collection_association, user):
        annotation = 'a'
        obj = cls_()
        obj.user = user
        obj.dataset_collection = library_dataset_collection_association
        obj.annotation = annotation

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.library_dataset_collection_id == library_dataset_collection_association.id
            assert stored_obj.user_id == user.id
            assert stored_obj.annotation == annotation

    def test_relationships(self, session, cls_, library_dataset_collection_association, user):
        obj = cls_()
        obj.user = user
        obj.dataset_collection = library_dataset_collection_association

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.dataset_collection.id == library_dataset_collection_association.id
            assert stored_obj.user.id == user.id


class TestLibraryDatasetCollectionTagAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'library_dataset_collection_tag_association'

    def test_columns(self, session, cls_, library_dataset_collection_association, tag, user):
        user_tname, value, user_value = 'a', 'b', 'c'
        obj = cls_(user=user, tag=tag, user_tname=user_tname, value=value)
        obj.user_value = user_value
        obj.dataset_collection = library_dataset_collection_association

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.library_dataset_collection_id == library_dataset_collection_association.id
            assert stored_obj.tag_id == tag.id
            assert stored_obj.user_id == user.id
            assert stored_obj.user_tname == user_tname
            assert stored_obj.value == value
            assert stored_obj.user_value == user_value

    def test_relationships(self, session, cls_, library_dataset_collection_association, tag, user):
        obj = cls_(user=user, tag=tag)
        obj.dataset_collection = library_dataset_collection_association

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.dataset_collection.id == library_dataset_collection_association.id
            assert stored_obj.tag.id == tag.id
            assert stored_obj.user.id == user.id


class TestLibraryDatasetCollectionRatingAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'library_dataset_collection_rating_association'

    def test_columns(self, session, cls_, library_dataset_collection_association, user):
        rating = 9
        obj = cls_(user, library_dataset_collection_association, rating)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.library_dataset_collection_id == library_dataset_collection_association.id
            assert stored_obj.user_id == user.id
            assert stored_obj.rating == rating

    def test_relationships(self, session, cls_, library_dataset_collection_association, user):
        obj = cls_(user, library_dataset_collection_association, 1)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.dataset_collection.id == library_dataset_collection_association.id
            assert stored_obj.user.id == user.id


class TestLibraryDatasetDatasetAssociationPermissions(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'library_dataset_dataset_association_permissions'

    def test_columns(self, session, cls_, library_dataset_dataset_association, role):
        action = 'a'
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_(action, library_dataset_dataset_association, role)
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.action == action
            assert stored_obj.library_dataset_dataset_association_id == library_dataset_dataset_association.id
            assert stored_obj.role_id == role.id

    def test_relationships(self, session, cls_, library_dataset_dataset_association, role):
        obj = cls_(None, library_dataset_dataset_association, role)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.library_dataset_dataset_association.id == library_dataset_dataset_association.id
            assert stored_obj.role.id == role.id


class TestLibraryDatasetDatasetAssociationTagAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'library_dataset_dataset_association_tag_association'

    def test_columns(self, session, cls_, library_dataset_dataset_association, tag, user):
        user_tname, value, user_value = 'a', 'b', 'c'
        obj = cls_(user=user, tag=tag, user_tname=user_tname, value=value)
        obj.user_value = user_value
        obj.library_dataset_dataset_association = library_dataset_dataset_association

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.library_dataset_dataset_association_id == library_dataset_dataset_association.id
            assert stored_obj.tag_id == tag.id
            assert stored_obj.user_id == user.id
            assert stored_obj.user_tname == user_tname
            assert stored_obj.value == value
            assert stored_obj.user_value == user_value

    def test_relationships(self, session, cls_, library_dataset_dataset_association, tag, user):
        obj = cls_(user=user, tag=tag)
        obj.library_dataset_dataset_association = library_dataset_dataset_association

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.library_dataset_dataset_association.id == library_dataset_dataset_association.id
            assert stored_obj.tag.id == tag.id
            assert stored_obj.user.id == user.id


class TestLibraryDatasetPermissions(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'library_dataset_permissions'

    def test_columns(self, session, cls_, library_dataset, role):
        action = 'a'
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_(action, library_dataset, role)
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.action == action
            assert stored_obj.library_dataset_id == library_dataset.id
            assert stored_obj.role_id == role.id

    def test_relationships(self, session, cls_, library_dataset, role):
        obj = cls_(None, library_dataset, role)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.library_dataset.id == library_dataset.id
            assert stored_obj.role.id == role.id


class TestLibraryFolder(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'library_folder'
        assert has_index(cls_.__table__, ('name',))

    def test_columns(self, session, cls_, library_folder):
        parent = library_folder
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        name = 'a'
        description = 'b'
        order_id = 9
        item_count = 1
        deleted = False
        purged = False
        genome_build = 'c'

        obj = cls_()
        obj.parent = parent
        obj.create_time = create_time
        obj.update_time = update_time
        obj.name = name
        obj.description = description
        obj.order_id = order_id
        obj.item_count = item_count
        obj.deleted = deleted
        obj.purged = purged
        obj.genome_build = genome_build

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.parent_id == parent.id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.name == name
            assert stored_obj.description == description
            assert stored_obj.order_id == order_id
            assert stored_obj.item_count == item_count
            assert stored_obj.deleted == deleted
            assert stored_obj.purged == purged
            assert stored_obj.genome_build == genome_build

    def test_relationships(
            self, session, cls_, model, library_folder, library_dataset, library, library_folder_permission):
        obj = cls_()
        obj.parent = library_folder
        folder1 = model.LibraryFolder()
        obj.folders.append(folder1)
        obj.library_root.append(library)
        obj.actions.append(library_folder_permission)

        # There's no back reference, so dataset does not update folder; so we have to flush to the database
        # via dbcleanup() context manager. TODO: ..but why is there no back reference?
        library_dataset.folder = obj

        with dbcleanup(session, obj) as obj_id, dbcleanup(session, library_dataset):
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.parent.id == library_folder.id
            assert stored_obj.folders == [folder1]
            assert stored_obj.active_folders == [folder1]
            assert stored_obj.library_root == [library]
            assert stored_obj.actions == [library_folder_permission]
            # use identity equality instread of object equality.
            assert stored_obj.datasets[0].id == library_dataset.id
            assert stored_obj.active_datasets[0].id == library_dataset.id


class TestLibraryFolderPermissions(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'library_folder_permissions'

    def test_columns(self, session, cls_, library_folder, role):
        action = 'a'
        obj = cls_(action, library_folder, role)
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.action == action
            assert stored_obj.library_folder_id == library_folder.id
            assert stored_obj.role_id == role.id

    def test_relationships(self, session, cls_, library_folder, role):
        obj = cls_(None, library_folder, role)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.folder.id == library_folder.id
            assert stored_obj.role.id == role.id


class TestLibraryInfoAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'library_info_association'

    def test_columns(self, session, cls_, library, form_definition, form_values):
        inheritable, deleted = True, True
        obj = cls_(library, form_definition, form_values, inheritable)
        obj.deleted = deleted

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.library_id == library.id
            assert stored_obj.form_definition_id == form_definition.id
            assert stored_obj.form_values_id == form_values.id
            assert stored_obj.inheritable == inheritable
            assert stored_obj.deleted == deleted

    def test_relationships(self, session, cls_, library, form_definition, form_values):
        obj = cls_(library, form_definition, form_values, None)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.library.id == library.id
            assert stored_obj.template.id == form_definition.id
            assert stored_obj.info.id == form_values.id


class TestLibraryPermissions(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'library_permissions'

    def test_columns(self, session, cls_, library, role):
        action = 'a'
        obj = cls_(action, library, role)
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_(action, library, role)
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.action == action
            assert stored_obj.library_id == library.id
            assert stored_obj.role_id == role.id

    def test_relationships(self, session, cls_, library, role):
        obj = cls_(None, library, role)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.library.id == library.id
            assert stored_obj.role.id == role.id


class TestPage(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'page'
        assert has_index(cls_.__table__, ('slug',))

    def test_columns(self, session, cls_, user, page_revision):
        title, deleted, importable, slug, published = 'a', True, True, 'b', True
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_()
        obj.user = user
        obj.title = title
        obj.deleted = deleted
        obj.importable = importable
        obj.slug = slug
        obj.published = published
        obj.create_time = create_time
        obj.update_time = update_time
        # This is OK for this test; however, page_revision.page != obj. Can we do better?
        obj.latest_revision = page_revision

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.user_id == user.id
            assert stored_obj.latest_revision_id == page_revision.id
            assert stored_obj.title == title
            assert stored_obj.deleted == deleted
            assert stored_obj.importable == importable
            assert stored_obj.slug == slug
            assert stored_obj.published == published

    def test_relationships(
        self,
        session,
        cls_,
        user,
        page_revision,
        page_tag_association,
        page_annotation_association,
        page_rating_association,
        page_user_share_association,
    ):
        obj = cls_()
        obj.user = user
        # This is OK for this test; however, page_revision.page != obj. Can we do better?
        obj.latest_revision = page_revision
        obj.revisions.append(page_revision)
        obj.tags.append(page_tag_association)
        obj.annotations.append(page_annotation_association)
        obj.ratings.append(page_rating_association)
        obj.users_shared_with.append(page_user_share_association)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.user.id == user.id
            assert stored_obj.revisions == [page_revision]
            assert stored_obj.latest_revision.id == page_revision.id
            assert stored_obj.tags == [page_tag_association]
            assert stored_obj.annotations == [page_annotation_association]
            assert stored_obj.ratings == [page_rating_association]
            assert stored_obj.users_shared_with == [page_user_share_association]
            # This doesn't test the average amount, just the mapping.
            assert stored_obj.average_rating == page_rating_association.rating

    def test_average_rating(self, model, session, page, user):
        # Page has been expunged; to access its deferred properties,
        # it needs to be added back to the session.
        session.add(page)
        assert page.average_rating is None  # With no ratings, we expect None.
        # Create ratings
        to_cleanup = []
        for rating in (1, 2, 3, 4, 5):
            page_rating_assoc = model.PageRatingAssociation(user, page)
            page_rating_assoc.rating = rating
            persist(session, page_rating_assoc)
            to_cleanup.append(page_rating_assoc)
        assert page.average_rating == 3.0  # Expect average after ratings added.
        # Cleanup: remove ratings from database
        delete_from_database(session, to_cleanup)


class TestPageAnnotationAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'page_annotation_association'
        assert has_index(cls_.__table__, ('annotation',))

    def test_columns(self, session, cls_, page, user):
        annotation = 'a'
        obj = cls_()
        obj.user = user
        obj.page = page
        obj.annotation = annotation

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.page_id == page.id
            assert stored_obj.user_id == user.id
            assert stored_obj.annotation == annotation

    def test_relationships(self, session, cls_, page, user):
        obj = cls_()
        obj.user = user
        obj.page = page

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.page.id == page.id
            assert stored_obj.user.id == user.id


class TestPageRatingAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'page_rating_association'

    def test_columns(self, session, cls_, page, user):
        rating = 9
        obj = cls_(user, page, rating)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.page_id == page.id
            assert stored_obj.user_id == user.id
            assert stored_obj.rating == rating

    def test_relationships(self, session, cls_, page, user):
        obj = cls_(user, page, 1)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.page.id == page.id
            assert stored_obj.user.id == user.id


class TestPageRevision(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'page_revision'

    def test_columns(self, session, cls_, model, page):
        title, content = 'a', 'b'
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_()
        obj.page = page
        obj.create_time = create_time
        obj.update_time = update_time
        obj.title = title
        obj.content = content

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.page_id == page.id
            assert stored_obj.title == title
            assert stored_obj.content == content
            assert stored_obj.content_format == model.PageRevision.DEFAULT_CONTENT_FORMAT

    def test_relationships(self, session, cls_, page):
        obj = cls_()
        obj.page = page

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.page.id == page.id


class TestPageTagAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'page_tag_association'

    def test_columns(self, session, cls_, page, tag, user):
        user_tname, value, user_value = 'a', 'b', 'c'
        obj = cls_(user=user, tag=tag, user_tname=user_tname, value=value)
        obj.user_value = user_value
        obj.page = page

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.page_id == page.id
            assert stored_obj.tag_id == tag.id
            assert stored_obj.user_id == user.id
            assert stored_obj.user_tname == user_tname
            assert stored_obj.value == value
            assert stored_obj.user_value == user_value

    def test_relationships(self, session, cls_, page, tag, user):
        obj = cls_(user=user, tag=tag)
        obj.page = page

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.page.id == page.id
            assert stored_obj.tag.id == tag.id
            assert stored_obj.user.id == user.id


class TestPageUserShareAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'page_user_share_association'

    def test_columns(self, session, cls_, page, user):
        obj = cls_()
        obj.page = page
        obj.user = user

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.page_id == page.id
            assert stored_obj.user_id == user.id

    def test_relationships(self, session, cls_, page, user):
        obj = cls_()
        obj.page = page
        obj.user = user

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.page.id == page.id
            assert stored_obj.user.id == user.id


class TestPasswordResetToken(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'password_reset_token'

    def test_columns_and_relationships(self, session, cls_, user):
        token = get_random_string()
        expiration_time = datetime.now()
        obj = cls_(user, token)
        obj.expiration_time = expiration_time

        where_clause = cls_.token == token

        with dbcleanup(session, obj, where_clause):
            stored_obj = get_stored_obj(session, cls_, where_clause=where_clause)
            # test columns
            assert stored_obj.token == token
            assert stored_obj.expiration_time == expiration_time
            assert stored_obj.user_id == user.id
            # test relationships
            assert stored_obj.user.id == user.id


class TestPostJobAction(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'post_job_action'

    def test_columns(self, session, cls_, workflow_step):
        action_type = 'a'
        output_name = 'b'
        action_arguments = 'c'
        obj = cls_(action_type, workflow_step, output_name, action_arguments)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.workflow_step_id == workflow_step.id
            assert stored_obj.action_type == action_type
            assert stored_obj.output_name == output_name
            assert stored_obj.action_arguments == action_arguments

    def test_relationships(self, session, cls_, workflow_step):
        obj = cls_('a', workflow_step, None, None)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.workflow_step.id == workflow_step.id


class TestPostJobActionAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'post_job_action_association'

    def test_columns(self, session, cls_, job, post_job_action):
        obj = cls_(post_job_action, job)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.job_id == job.id
            assert stored_obj.post_job_action_id == post_job_action.id

    def test_relationships(self, session, cls_, job, post_job_action):
        obj = cls_(post_job_action, job)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id
            assert stored_obj.post_job_action.id == post_job_action.id


class TestPSAAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'psa_association'

    def test_columns(self, session, cls_):
        server_url, handle, secret, issued, lifetime, assoc_type = 'a', 'b', 'c', 1, 2, 'd'
        obj = cls_(server_url, handle, secret, issued, lifetime, assoc_type)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.server_url == server_url
            assert stored_obj.handle == handle
            assert stored_obj.secret == secret
            assert stored_obj.issued == issued
            assert stored_obj.lifetime == lifetime
            assert stored_obj.assoc_type == assoc_type


class TestPSACode(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'psa_code'
        assert has_unique_constraint(cls_.__table__, ('code', 'email'))

    def test_columns(self, session, cls_):
        email, code = 'a', get_random_string()
        obj = cls_(email, code)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.email == email
            assert stored_obj.code == code


class TestPSANonce(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'psa_nonce'

    def test_columns(self, session, cls_):
        server_url, timestamp, salt = 'a', 1, 'b'
        obj = cls_(server_url, timestamp, salt)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.server_url
            assert stored_obj.timestamp == timestamp
            assert stored_obj.salt == salt


class TestPSAPartial(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'psa_partial'

    def test_columns(self, session, cls_):
        token, data, next_step, backend = 'a', 'b', 1, 'c'
        obj = cls_(token, data, next_step, backend)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.token == token
            assert stored_obj.data == data
            assert stored_obj.next_step == next_step
            assert stored_obj.backend == backend


class TestQuota(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'quota'

    def test_columns(self, session, cls_):
        name, description, amount, operation = get_random_string(), 'b', 42, '+'
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_(name, description, amount, operation)
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.name == name
            assert stored_obj.description == description
            assert stored_obj.bytes == amount
            assert stored_obj.operation == operation
            assert stored_obj.deleted is False

    def test_relationships(self, session, cls_, default_quota_association, group_quota_association, user_quota_association):

        def add_association(assoc_object, assoc_attribute):
            assoc_object.quota = obj
            getattr(obj, assoc_attribute).append(assoc_object)

        obj = cls_(None, None, 1, '+')
        add_association(default_quota_association, 'default')
        add_association(group_quota_association, 'groups')
        add_association(user_quota_association, 'users')

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.default == [default_quota_association]
            assert stored_obj.groups == [group_quota_association]
            assert stored_obj.users == [user_quota_association]


class TestRole(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'role'

    def test_columns(self, session, cls_):
        name, description, type_, deleted = get_random_string(), 'b', cls_.types.SYSTEM, True
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_(name, description, type_, deleted)
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.name == name
            assert stored_obj.description == description
            assert stored_obj.type == type_
            assert stored_obj.deleted == deleted

    def test_relationships(
        self,
        session,
        cls_,
        dataset_permission,
        group_role_association,
        library_permission,
        library_folder_permission,
        library_dataset_permission,
        library_dataset_dataset_association_permission,
    ):
        name, description, type_ = get_random_string(), 'b', cls_.types.SYSTEM
        obj = cls_(name, description, type_)
        obj.dataset_actions.append(dataset_permission)
        obj.library_actions.append(library_permission)
        obj.library_folder_actions.append(library_folder_permission)
        obj.library_dataset_actions.append(library_dataset_permission)
        obj.library_dataset_dataset_actions.append(library_dataset_dataset_association_permission)
        obj.groups.append(group_role_association)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.dataset_actions == [dataset_permission]
            assert stored_obj.groups == [group_role_association]
            assert stored_obj.library_actions == [library_permission]
            assert stored_obj.library_folder_actions == [library_folder_permission]
            assert stored_obj.library_dataset_actions == [library_dataset_permission]
            assert stored_obj.library_dataset_dataset_actions == [library_dataset_dataset_association_permission]


class TestStoredWorkflowAnnotationAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'stored_workflow_annotation_association'
        assert has_index(cls_.__table__, ('annotation',))

    def test_columns(self, session, cls_, stored_workflow, user):
        annotation = 'a'
        obj = cls_()
        obj.stored_workflow = stored_workflow
        obj.user = user
        obj.annotation = annotation

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.stored_workflow_id == stored_workflow.id
            assert stored_obj.user_id == user.id
            assert stored_obj.annotation == annotation

    def test_relationships(self, session, cls_, stored_workflow, user):
        obj = cls_()
        obj.stored_workflow = stored_workflow
        obj.user = user

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.stored_workflow.id == stored_workflow.id
            assert stored_obj.user.id == user.id


class TestStoredWorkflowRatingAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'stored_workflow_rating_association'

    def test_columns(self, session, cls_, stored_workflow, user):
        rating = 9
        obj = cls_(user, stored_workflow, rating)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.stored_workflow_id == stored_workflow.id
            assert stored_obj.user_id == user.id
            assert stored_obj.rating == rating

    def test_relationships(self, session, cls_, stored_workflow, user):
        obj = cls_(user, stored_workflow, 1)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.stored_workflow.id == stored_workflow.id
            assert stored_obj.user.id == user.id


class TestStoredWorkflowTagAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'stored_workflow_tag_association'

    def test_columns(self, session, cls_, stored_workflow, tag, user):
        user_tname, value, user_value = 'a', 'b', 'c'
        obj = cls_(user=user, tag=tag, user_tname=user_tname, value=value)
        obj.user_value = user_value
        obj.stored_workflow = stored_workflow

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.stored_workflow_id == stored_workflow.id
            assert stored_obj.tag_id == tag.id
            assert stored_obj.user_id == user.id
            assert stored_obj.user_tname == user_tname
            assert stored_obj.value == value
            assert stored_obj.user_value == user_value

    def test_relationships(self, session, cls_, stored_workflow, tag, user):
        obj = cls_(user=user, tag=tag)
        obj.stored_workflow = stored_workflow

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.stored_workflow.id == stored_workflow.id
            assert stored_obj.tag.id == tag.id
            assert stored_obj.user.id == user.id


class TestTag(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'tag'
        assert has_unique_constraint(cls_.__table__, ('name',))

    def test_columns(self, session, cls_):
        parent_tag = cls_()
        type_, name = 1, 'a'
        obj = cls_(type=type_, name=name)
        obj.parent = parent_tag

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.type == type_
            assert stored_obj.parent_id == parent_tag.id
            assert stored_obj.name == name

    def test_relationships(
        self,
        session,
        cls_,
        history_tag_association,
        history_dataset_association_tag_association,
        library_dataset_dataset_association_tag_association,
        page_tag_association,
        workflow_step_tag_association,
        stored_workflow_tag_association,
        visualization_tag_association,
        history_dataset_collection_tag_association,
        library_dataset_collection_tag_association,
        tool_tag_association,
    ):
        obj = cls_()
        parent_tag = cls_()
        child_tag = cls_()
        obj.parent = parent_tag
        obj.children.append(child_tag)

        def add_association(assoc_object, assoc_attribute):
            assoc_object.tag = obj
            getattr(obj, assoc_attribute).append(assoc_object)

        add_association(history_tag_association, 'tagged_histories')
        add_association(history_dataset_association_tag_association, 'tagged_history_dataset_associations')
        add_association(library_dataset_dataset_association_tag_association, 'tagged_library_dataset_dataset_associations')
        add_association(page_tag_association, 'tagged_pages')
        add_association(workflow_step_tag_association, 'tagged_workflow_steps')
        add_association(stored_workflow_tag_association, 'tagged_stored_workflows')
        add_association(visualization_tag_association, 'tagged_visualizations')
        add_association(history_dataset_collection_tag_association, 'tagged_history_dataset_collections')
        add_association(library_dataset_collection_tag_association, 'tagged_library_dataset_collections')
        add_association(tool_tag_association, 'tagged_tools')

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.parent.id == parent_tag.id
            assert stored_obj.children == [child_tag]
            assert stored_obj.tagged_histories == [history_tag_association]
            assert stored_obj.tagged_history_dataset_associations == [history_dataset_association_tag_association]
            assert stored_obj.tagged_library_dataset_dataset_associations == [library_dataset_dataset_association_tag_association]
            assert stored_obj.tagged_pages == [page_tag_association]
            assert stored_obj.tagged_workflow_steps == [workflow_step_tag_association]
            assert stored_obj.tagged_stored_workflows == [stored_workflow_tag_association]
            assert stored_obj.tagged_visualizations == [visualization_tag_association]
            assert stored_obj.tagged_history_dataset_collections == [history_dataset_collection_tag_association]
            assert stored_obj.tagged_library_dataset_collections == [library_dataset_collection_tag_association]
            assert stored_obj.tagged_tools == [tool_tag_association]


class TestTask(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'task'

    def test_columns(self, session, cls_, model, job):
        create_time = datetime.now()
        execution_time = create_time + timedelta(hours=1)
        update_time = execution_time + timedelta(hours=1)
        state = model.Task.states.WAITING
        command_line = 'a'
        param_filename = 'b'
        runner_name = 'c'
        job_stdout = 'd'
        job_stderr = 'e'
        tool_stdout = 'f'
        tool_stderr = 'g'
        exit_code = 9
        job_messages = 'h'
        info = 'i'
        traceback = 'j'
        working_directory = 'k'
        task_runner_name = 'l'
        task_runner_external_id = 'm'
        prepare_input_files_cmd = 'n'

        obj = cls_(job, working_directory, prepare_input_files_cmd)
        obj.create_time = create_time
        obj.execution_time = execution_time
        obj.update_time = update_time
        obj.state = state
        obj.command_line = command_line
        obj.param_filename = param_filename
        obj.runner_name = runner_name
        obj.job_stdout = job_stdout
        obj.job_stderr = job_stderr
        obj.tool_stdout = tool_stdout
        obj.tool_stderr = tool_stderr
        obj.exit_code = exit_code
        obj.job_messages = job_messages
        obj.info = info
        obj.traceback = traceback
        obj.task_runner_name = task_runner_name
        obj.task_runner_external_id = task_runner_external_id

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.execution_time == execution_time
            assert stored_obj.update_time == update_time
            assert stored_obj.state == state
            assert stored_obj.command_line == command_line
            assert stored_obj.param_filename == param_filename
            assert stored_obj.runner_name == runner_name
            assert stored_obj.job_stdout == job_stdout
            assert stored_obj.job_stderr == job_stderr
            assert stored_obj.tool_stdout == tool_stdout
            assert stored_obj.tool_stderr == tool_stderr
            assert stored_obj.exit_code == exit_code
            assert stored_obj.job_messages == job_messages
            assert stored_obj.info == info
            assert stored_obj.traceback == traceback
            assert stored_obj.task_runner_name == task_runner_name
            assert stored_obj.task_runner_external_id == task_runner_external_id

    def test_relationships(self, session, cls_, job, task_metric_numeric, task_metric_text):
        obj = cls_(job, None, None)
        obj.numeric_metrics.append(task_metric_numeric)
        obj.text_metrics.append(task_metric_text)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id
            assert stored_obj.numeric_metrics == [task_metric_numeric]
            assert stored_obj.text_metrics == [task_metric_text]


class TestTaskMetricNumeric(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'task_metric_numeric'

    def test_columns(self, session, cls_, task):
        plugin, metric_name, metric_value = 'a', 'b', 9
        obj = cls_(plugin, metric_name, metric_value)
        obj.task = task

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.task_id == task.id
            assert stored_obj.plugin == plugin
            assert stored_obj.metric_value == metric_value

    def test_relationships(self, session, cls_, task):
        obj = cls_(None, None, None)
        obj.task = task

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.task.id == task.id


class TestTaskMetricText(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'task_metric_text'

    def test_columns(self, session, cls_, task):
        plugin, metric_name, metric_value = 'a', 'b', 'c'
        obj = cls_(plugin, metric_name, metric_value)
        obj.task = task

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.task_id == task.id
            assert stored_obj.plugin == plugin
            assert stored_obj.metric_value == metric_value

    def test_relationships(self, session, cls_, task):
        obj = cls_(None, None, None)
        obj.task = task

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.task.id == task.id


class TestToolTagAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'tool_tag_association'

    def test_columns(self, session, cls_, tag, user):
        user_tname, value, user_value, tool_id = 'a', 'b', 'c', 'd'
        obj = cls_(user=user, tag=tag, user_tname=user_tname, value=value)
        obj.user_value = user_value
        obj.tool_id = tool_id

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.tool_id == tool_id
            assert stored_obj.tag_id == tag.id
            assert stored_obj.user_id == user.id
            assert stored_obj.user_tname == user_tname
            assert stored_obj.value == value
            assert stored_obj.user_value == user_value

    def test_relationships(self, session, cls_, tag, user):
        obj = cls_(user=user, tag=tag)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.tag.id == tag.id
            assert stored_obj.user.id == user.id


class TestTransferJob(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'transfer_job'

    def test_columns(self, session, cls_, model):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        state, path, info, pid, socket, params = model.TransferJob.states.NEW, 'a', 'b', 2, 3, 'c'
        obj = cls_(state, path, info, pid, socket, params)
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.state == state
            assert stored_obj.path == path
            assert stored_obj.info == info
            assert stored_obj.pid == pid
            assert stored_obj.socket == socket
            assert stored_obj.params == params

    def test_relationships(self, session, cls_, genome_index_tool_data):
        obj = cls_()
        obj.transfer_job.append(genome_index_tool_data)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.transfer_job == [genome_index_tool_data]


class TestUserAction(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'user_action'

    def test_columns(self, session, cls_, user, galaxy_session):
        action, params, context = 'a', 'b', 'c'
        create_time = datetime.now()
        obj = cls_(user, galaxy_session.id, action, params, context)
        obj.create_time = create_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.user_id == user.id
            assert stored_obj.session_id == galaxy_session.id
            assert stored_obj.action == action
            assert stored_obj.context == context
            assert stored_obj.params == params

    def test_relationships(self, session, cls_, user, galaxy_session):
        obj = cls_(user, galaxy_session.id, None, None, None)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.user.id == user.id


class TestUserAddress(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'user_address'

    def test_columns_and_relationships(self, session, cls_, user):
        desc, name, institution, address, city, state, postal_code, country, phone, deleted, purged = \
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', True, False
        obj = cls_(user, desc, name, institution, address, city, state, postal_code, country, phone)
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj.create_time = create_time
        obj.update_time = update_time
        obj.deleted = deleted
        obj.purged = purged

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            # test columns
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.user_id == user.id
            assert stored_obj.desc == desc
            assert stored_obj.name == name
            assert stored_obj.institution == institution
            assert stored_obj.address == address
            assert stored_obj.city == city
            assert stored_obj.state == state
            assert stored_obj.postal_code == postal_code
            assert stored_obj.country == country
            assert stored_obj.phone == phone
            assert stored_obj.deleted == deleted
            assert stored_obj.purged == purged
            # test relationships
            assert stored_obj.user.id == user.id


class TestUserAuthnzToken(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'oidc_user_authnz_tokens'
        assert has_unique_constraint(cls_.__table__, ('provider', 'uid'))

    def test_columns(self, session, cls_, user):
        provider, uid, extra_data, lifetime, assoc_type = get_random_string(), 'b', 'c', 1, 'd'
        obj = cls_(provider, uid, extra_data, lifetime, assoc_type, user)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.user_id == user.id
            assert stored_obj.uid == uid
            assert stored_obj.provider == provider
            assert stored_obj.extra_data == extra_data
            assert stored_obj.lifetime == lifetime
            assert stored_obj.assoc_type == assoc_type

    def test_relationships(self, session, cls_, user, cloud_authz):
        obj = cls_(get_random_string(), None, user=user)
        obj.cloudauthz.append(cloud_authz)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.cloudauthz == [cloud_authz]
            assert stored_obj.user.id == user.id


class TestUserGroupAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'user_group_association'

    def test_columns(self, session, cls_, user, group):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_(user, group)
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.user_id == user.id
            assert stored_obj.group_id == group.id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time

    def test_relationships(self, session, cls_, user, group):
        obj = cls_(user, group)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.user.id == user.id
            assert stored_obj.group.id == group.id


class TestUserQuotaAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'user_quota_association'

    def test_columns(self, session, cls_, user, quota):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_(user, quota)
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.user_id == user.id
            assert stored_obj.quota_id == quota.id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time

    def test_relationships(self, session, cls_, user, quota):
        obj = cls_(user, quota)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.user.id == user.id
            assert stored_obj.quota.id == quota.id


class TestVisualizationAnnotationAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'visualization_annotation_association'
        assert has_index(cls_.__table__, ('annotation',))

    def test_columns(self, session, cls_, visualization, user):
        annotation = 'a'
        obj = cls_()
        obj.user = user
        obj.visualization = visualization
        obj.annotation = annotation

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.visualization_id == visualization.id
            assert stored_obj.user_id == user.id
            assert stored_obj.annotation == annotation

    def test_relationships(self, session, cls_, visualization, user):
        obj = cls_()
        obj.user = user
        obj.visualization = visualization

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.visualization.id == visualization.id
            assert stored_obj.user.id == user.id


class TestVisualizationRatingAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'visualization_rating_association'

    def test_columns(self, session, cls_, visualization, user):
        rating = 9
        obj = cls_(user, visualization, rating)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.visualization_id == visualization.id
            assert stored_obj.user_id == user.id
            assert stored_obj.rating == rating

    def test_relationships(self, session, cls_, visualization, user):
        obj = cls_(user, visualization, 1)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.visualization.id == visualization.id
            assert stored_obj.user.id == user.id


class TestVisualizationRevision(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'visualization_revision'
        assert has_index(cls_.__table__, ('dbkey',))

    def test_columns(self, session, cls_, visualization):
        visualization, title, dbkey, config = visualization, 'a', 'b', 'c'
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_(visualization, title, dbkey, config)
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.visualization_id == visualization.id
            assert stored_obj.title == title
            assert stored_obj.dbkey == dbkey
            assert stored_obj.config == config

    def test_relationships(self, session, cls_, visualization):
        obj = cls_(visualization)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.visualization.id == visualization.id


class TestWorkerProcess(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'worker_process'
        assert has_unique_constraint(cls_.__table__, ('server_name', 'hostname'))

    def test_columns(self, session, cls_):
        server_name, hostname = get_random_string(), 'a'
        update_time = datetime.now()
        obj = cls_(server_name, hostname)
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.server_name == server_name
            assert stored_obj.hostname == hostname
            assert stored_obj.pid is None
            assert stored_obj.update_time == update_time


class TestWorkflowRequestInputStepParameter(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'workflow_request_input_step_parameter'

    def test_columns(self, session, cls_, workflow_step, workflow_invocation):
        parameter_value = 'a'
        obj = cls_()
        obj.workflow_invocation = workflow_invocation
        obj.workflow_step = workflow_step
        obj.parameter_value = parameter_value

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.workflow_invocation_id == workflow_invocation.id
            assert stored_obj.workflow_step_id == workflow_step.id
            assert stored_obj.parameter_value == parameter_value

    def test_relationships(self, session, cls_, workflow_step, workflow_invocation):
        obj = cls_()
        obj.workflow_invocation = workflow_invocation
        obj.workflow_step = workflow_step

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.workflow_invocation.id == workflow_invocation.id
            assert stored_obj.workflow_step.id == workflow_step.id


class TestWorkflowRequestStepState(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'workflow_request_step_states'

    def test_columns(self, session, cls_, workflow_step, workflow_invocation):
        value = 'a'
        obj = cls_(workflow_step, None, value)
        obj.workflow_invocation = workflow_invocation

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.workflow_invocation_id == workflow_invocation.id
            assert stored_obj.workflow_step_id == workflow_step.id
            assert stored_obj.value == value

    def test_relationships(self, session, cls_, workflow_step, workflow_invocation):
        obj = cls_(workflow_step)
        obj.workflow_invocation = workflow_invocation

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.workflow_invocation.id == workflow_invocation.id
            assert stored_obj.workflow_step.id == workflow_step.id


class TestWorkflowRequestToInputDatasetAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'workflow_request_to_input_dataset'

    def test_columns(self, session, cls_, workflow_step, workflow_invocation, history_dataset_association):
        name = 'a'
        obj = cls_()
        obj.name = name
        obj.workflow_invocation = workflow_invocation
        obj.workflow_step = workflow_step
        obj.dataset = history_dataset_association

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.workflow_invocation_id == workflow_invocation.id
            assert stored_obj.workflow_step_id == workflow_step.id
            assert stored_obj.dataset_id == history_dataset_association.id

    def test_relationships(self, session, cls_, workflow_step, workflow_invocation, history_dataset_association):
        obj = cls_()
        obj.workflow_invocation = workflow_invocation
        obj.workflow_step = workflow_step
        obj.dataset = history_dataset_association

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.workflow_invocation.id == workflow_invocation.id
            assert stored_obj.workflow_step.id == workflow_step.id
            assert stored_obj.dataset_id == history_dataset_association.id


class TestWorkflowRequestToInputDatasetCollectionAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'workflow_request_to_input_collection_dataset'

    def test_columns(
        self,
        session,
        cls_,
        workflow_step,
        workflow_invocation,
        history_dataset_collection_association
    ):
        name = 'a'
        obj = cls_()
        obj.name = name
        obj.workflow_invocation = workflow_invocation
        obj.workflow_step = workflow_step
        obj.dataset_collection = history_dataset_collection_association

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.workflow_invocation_id == workflow_invocation.id
            assert stored_obj.workflow_step_id == workflow_step.id
            assert stored_obj.dataset_collection_id == history_dataset_collection_association.id

    def test_relationships(
        self,
        session,
        cls_,
        workflow_step,
        workflow_invocation,
        history_dataset_collection_association
    ):
        obj = cls_()
        obj.workflow_invocation = workflow_invocation
        obj.workflow_step = workflow_step
        obj.dataset_collection = history_dataset_collection_association

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.workflow_invocation.id == workflow_invocation.id
            assert stored_obj.workflow_step.id == workflow_step.id
            assert stored_obj.dataset_collection.id == history_dataset_collection_association.id


class TestWorkflowStepAnnotationAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'workflow_step_annotation_association'
        assert has_index(cls_.__table__, ('annotation',))

    def test_columns(self, session, cls_, workflow_step, user):
        annotation = 'a'
        obj = cls_()
        obj.user = user
        obj.workflow_step = workflow_step
        obj.annotation = annotation

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.workflow_step_id == workflow_step.id
            assert stored_obj.user_id == user.id
            assert stored_obj.annotation == annotation

    def test_relationships(self, session, cls_, workflow_step, user):
        obj = cls_()
        obj.user = user
        obj.workflow_step = workflow_step

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.workflow_step.id == workflow_step.id
            assert stored_obj.user.id == user.id


class TestWorkflowStepTagAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'workflow_step_tag_association'

    def test_columns(self, session, cls_, workflow_step, tag, user):
        user_tname, value, user_value = 'a', 'b', 'c'
        obj = cls_(user=user, tag=tag, user_tname=user_tname, value=value)
        obj.user_value = user_value
        obj.workflow_step = workflow_step

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.workflow_step_id == workflow_step.id
            assert stored_obj.tag_id == tag.id
            assert stored_obj.user_id == user.id
            assert stored_obj.user_tname == user_tname
            assert stored_obj.value == value
            assert stored_obj.user_value == user_value

    def test_relationships(self, session, cls_, workflow_step, tag, user):
        obj = cls_(user=user, tag=tag)
        obj.workflow_step = workflow_step

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.workflow_step.id == workflow_step.id
            assert stored_obj.tag.id == tag.id
            assert stored_obj.user.id == user.id


class TestVisualizationTagAssociation(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'visualization_tag_association'

    def test_columns(self, session, cls_, visualization, tag, user):
        user_tname, value, user_value = 'a', 'b', 'c'
        obj = cls_(user=user, tag=tag, user_tname=user_tname, value=value)
        obj.user_value = user_value
        obj.visualization = visualization

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.visualization_id == visualization.id
            assert stored_obj.tag_id == tag.id
            assert stored_obj.user_id == user.id
            assert stored_obj.user_tname == user_tname
            assert stored_obj.value == value
            assert stored_obj.user_value == user_value

    def test_relationships(self, session, cls_, visualization, tag, user):
        obj = cls_(user=user, tag=tag)
        obj.visualization = visualization

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.visualization.id == visualization.id
            assert stored_obj.tag.id == tag.id
            assert stored_obj.user.id == user.id


class TestWorkflowRequestInputParameter(BaseTest):

    def test_table(self, cls_):
        assert cls_.__tablename__ == 'workflow_request_input_parameters'

    def test_columns(self, session, cls_, workflow_invocation):
        name, value, type = 'a', 'b', 'c'
        obj = cls_(name, value, type)
        obj.workflow_invocation = workflow_invocation

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.workflow_invocation_id == workflow_invocation.id
            assert stored_obj.name == name
            assert stored_obj.value == value
            assert stored_obj.type == type

    def test_relationships(self, session, cls_, workflow_invocation):
        obj = cls_()
        obj.workflow_invocation = workflow_invocation

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.workflow_invocation.id == workflow_invocation.id


@pytest.fixture(scope='module')
def model():
    db_uri = 'sqlite:///:memory:'
    return mapping.init('/tmp', db_uri, create_tables=True)


@pytest.fixture
def session(model):
    Session = model.session
    yield Session()
    Session.remove()  # Ensures we get a new session for each test


@pytest.fixture
def cleanup_event(model, session):
    ce = model.CleanupEvent()
    yield from dbcleanup_wrapper(session, ce)


@pytest.fixture
def cloud_authz(model, session, user, user_authnz_token):
    ca = model.CloudAuthz(user.id, 'a', 'b', user_authnz_token.id, 'c')
    yield from dbcleanup_wrapper(session, ca)


@pytest.fixture
def dataset(model, session):
    d = model.Dataset()
    yield from dbcleanup_wrapper(session, d)


@pytest.fixture
def dataset_collection(model, session):
    dc = model.DatasetCollection(collection_type='a')
    yield from dbcleanup_wrapper(session, dc)


@pytest.fixture
def dataset_collection_element(
        model, session, dataset_collection, history_dataset_association):
    dce = model.DatasetCollectionElement(
        collection=dataset_collection, element=history_dataset_association)
    yield from dbcleanup_wrapper(session, dce)


@pytest.fixture
def dataset_hash(model, session):
    dh = model.DatasetHash()
    yield from dbcleanup_wrapper(session, dh)


@pytest.fixture
def dataset_permission(model, session, dataset):
    d = model.DatasetPermissions('a', dataset)
    yield from dbcleanup_wrapper(session, d)


@pytest.fixture
def dataset_source(model, session):
    d = model.DatasetSource()
    yield from dbcleanup_wrapper(session, d)


@pytest.fixture
def dataset_source_hash(model, session):
    d = model.DatasetSourceHash()
    yield from dbcleanup_wrapper(session, d)


@pytest.fixture
def default_history_permissions(model, session, history, role):
    dha = model.DefaultHistoryPermissions(history, 'a', role)
    yield from dbcleanup_wrapper(session, dha)


@pytest.fixture
def default_quota_association(model, session, quota):
    type_ = model.DefaultQuotaAssociation.types.REGISTERED
    dqa = model.DefaultQuotaAssociation(type_, quota)
    yield from dbcleanup_wrapper(session, dqa)


@pytest.fixture
def deferred_job(model, session):
    dj = model.DeferredJob()
    yield from dbcleanup_wrapper(session, dj)


@pytest.fixture
def extended_metadata(model, session):
    em = model.ExtendedMetadata(None)
    yield from dbcleanup_wrapper(session, em)


@pytest.fixture
def extended_metadata_index(model, session, extended_metadata):
    emi = model.ExtendedMetadataIndex(extended_metadata, None, None)
    yield from dbcleanup_wrapper(session, emi)


@pytest.fixture
def form_definition(model, session, form_definition_current):
    fd = model.FormDefinition(name='a', form_definition_current=form_definition_current)
    yield from dbcleanup_wrapper(session, fd)


@pytest.fixture
def form_definition_current(model, session):
    fdc = model.FormDefinitionCurrent()
    yield from dbcleanup_wrapper(session, fdc)


@pytest.fixture
def form_values(model, session):
    fv = model.FormValues()
    yield from dbcleanup_wrapper(session, fv)


@pytest.fixture
def galaxy_session(model, session, user):
    s = model.GalaxySession()
    yield from dbcleanup_wrapper(session, s)


@pytest.fixture
def galaxy_session_history_association(model, session, galaxy_session, history):
    sha = model.GalaxySessionToHistoryAssociation(galaxy_session, history)
    yield from dbcleanup_wrapper(session, sha)


@pytest.fixture
def genome_index_tool_data(model, session):
    gitd = model.GenomeIndexToolData()
    yield from dbcleanup_wrapper(session, gitd)


@pytest.fixture
def group(model, session):
    g = model.Group()
    yield from dbcleanup_wrapper(session, g)


@pytest.fixture
def group_quota_association(model, session):
    gqa = model.GroupQuotaAssociation(None, None)
    yield from dbcleanup_wrapper(session, gqa)


@pytest.fixture
def group_role_association(model, session):
    gra = model.GroupRoleAssociation(None, None)
    yield from dbcleanup_wrapper(session, gra)


@pytest.fixture
def history(model, session):
    h = model.History()
    yield from dbcleanup_wrapper(session, h)


@pytest.fixture
def history_annotation_association(model, session):
    haa = model.HistoryAnnotationAssociation()
    yield from dbcleanup_wrapper(session, haa)


@pytest.fixture
def history_dataset_association(model, session, dataset):
    hda = model.HistoryDatasetAssociation(dataset=dataset)
    yield from dbcleanup_wrapper(session, hda)


@pytest.fixture
def history_dataset_association_tag_association(model, session):
    hdata = model.HistoryDatasetAssociationTagAssociation()
    yield from dbcleanup_wrapper(session, hdata)


@pytest.fixture
def history_dataset_collection_association(model, session):
    hdca = model.HistoryDatasetCollectionAssociation()
    yield from dbcleanup_wrapper(session, hdca)


@pytest.fixture
def history_dataset_collection_tag_association(model, session):
    hdcta = model.HistoryDatasetCollectionTagAssociation()
    yield from dbcleanup_wrapper(session, hdcta)


@pytest.fixture
def history_rating_association(model, session, user, history):
    hda = model.HistoryRatingAssociation(user, history)
    yield from dbcleanup_wrapper(session, hda)


@pytest.fixture
def history_tag_association(model, session):
    hta = model.HistoryTagAssociation()
    yield from dbcleanup_wrapper(session, hta)


@pytest.fixture
def history_user_share_association(model, session):
    husa = model.HistoryUserShareAssociation()
    yield from dbcleanup_wrapper(session, husa)


@pytest.fixture
def implicit_collection_jobs(model, session):
    icj = model.ImplicitCollectionJobs(populated_state='new')
    yield from dbcleanup_wrapper(session, icj)


@pytest.fixture
def implicit_collection_jobs_job_association(model, session):
    icjja = model.ImplicitCollectionJobsJobAssociation()
    icjja.order_index = 1
    yield from dbcleanup_wrapper(session, icjja)


@pytest.fixture
def implicitly_converted_dataset_association(model, session, history_dataset_association):
    icda = model.ImplicitlyConvertedDatasetAssociation(
        dataset=history_dataset_association,
        parent=history_dataset_association,  # using the same dataset; should work here.
    )
    yield from dbcleanup_wrapper(session, icda)


@pytest.fixture
def job(model, session):
    j = model.Job()
    yield from dbcleanup_wrapper(session, j)


@pytest.fixture
def job_export_history_archive(model, session):
    jeha = model.JobExportHistoryArchive()
    yield from dbcleanup_wrapper(session, jeha)


@pytest.fixture
def library(model, session):
    lb = model.Library()
    yield from dbcleanup_wrapper(session, lb)


@pytest.fixture
def library_folder(model, session):
    lf = model.LibraryFolder()
    yield from dbcleanup_wrapper(session, lf)


@pytest.fixture
def library_dataset(model, session):
    ld = model.LibraryDataset()
    yield from dbcleanup_wrapper(session, ld)


@pytest.fixture
def library_dataset_collection_association(model, session):
    ldca = model.LibraryDatasetCollectionAssociation()
    yield from dbcleanup_wrapper(session, ldca)


@pytest.fixture
def library_dataset_collection_tag_association(model, session):
    ldcta = model.LibraryDatasetCollectionTagAssociation()
    yield from dbcleanup_wrapper(session, ldcta)


@pytest.fixture
def library_dataset_dataset_association(model, session):
    ldda = model.LibraryDatasetDatasetAssociation()
    yield from dbcleanup_wrapper(session, ldda)


@pytest.fixture
def library_dataset_dataset_association_tag_association(model, session):
    lddata = model.LibraryDatasetDatasetAssociationTagAssociation()
    yield from dbcleanup_wrapper(session, lddata)


@pytest.fixture
def library_dataset_permission(model, session, library_dataset, role):
    ldp = model.LibraryDatasetPermissions('a', library_dataset, role)
    yield from dbcleanup_wrapper(session, ldp)


@pytest.fixture
def library_dataset_dataset_association_permission(model, session, library_dataset_dataset_association, role):
    lddp = model.LibraryDatasetDatasetAssociationPermissions('a', library_dataset_dataset_association, role)
    yield from dbcleanup_wrapper(session, lddp)


@pytest.fixture
def library_folder_permission(model, session, library_folder, role):
    lfp = model.LibraryFolderPermissions('a', library_folder, role)
    yield from dbcleanup_wrapper(session, lfp)


@pytest.fixture
def library_info_association(model, session, library, form_definition, form_values):
    lia = model.LibraryInfoAssociation(library, form_definition, form_values)
    yield from dbcleanup_wrapper(session, lia)


@pytest.fixture
def library_permission(model, session, library, role):
    lp = model.LibraryPermissions('a', library, role)
    yield from dbcleanup_wrapper(session, lp)


@pytest.fixture
def metadata_file(model, session):
    mf = model.MetadataFile()
    yield from dbcleanup_wrapper(session, mf)


@pytest.fixture
def page(model, session, user):
    p = model.Page()
    p.user = user
    yield from dbcleanup_wrapper(session, p)


@pytest.fixture
def page_revision(model, session, page):
    pr = model.PageRevision()
    pr.page = page
    yield from dbcleanup_wrapper(session, pr)


@pytest.fixture
def page_annotation_association(model, session):
    paa = model.PageAnnotationAssociation()
    yield from dbcleanup_wrapper(session, paa)


@pytest.fixture
def page_rating_association(model, session):
    pra = model.PageRatingAssociation(None, None)
    yield from dbcleanup_wrapper(session, pra)


@pytest.fixture
def page_tag_association(model, session):
    pta = model.PageTagAssociation()
    yield from dbcleanup_wrapper(session, pta)


@pytest.fixture
def page_user_share_association(model, session):
    pra = model.PageUserShareAssociation()
    yield from dbcleanup_wrapper(session, pra)


@pytest.fixture
def post_job_action(model, session):
    pja = model.PostJobAction('a')
    yield from dbcleanup_wrapper(session, pja)


@pytest.fixture
def quota(model, session):
    q = model.Quota(get_random_string(), 'b')
    yield from dbcleanup_wrapper(session, q)


@pytest.fixture
def role(model, session):
    r = model.Role()
    yield from dbcleanup_wrapper(session, r)


@pytest.fixture
def stored_workflow(model, session, user):
    w = model.StoredWorkflow()
    w.user = user
    yield from dbcleanup_wrapper(session, w)


@pytest.fixture
def stored_workflow_tag_association(model, session):
    swta = model.StoredWorkflowTagAssociation()
    yield from dbcleanup_wrapper(session, swta)


@pytest.fixture
def tag(model, session):
    t = model.Tag()
    yield from dbcleanup_wrapper(session, t)


@pytest.fixture
def task(model, session, job):
    t = model.Task(job, 'a', 'b')
    yield from dbcleanup_wrapper(session, t)


@pytest.fixture
def task_metric_numeric(model, session):
    tmn = model. TaskMetricNumeric('a', 'b', 9)
    yield from dbcleanup_wrapper(session, tmn)


@pytest.fixture
def task_metric_text(model, session):
    tmt = model. TaskMetricText('a', 'b', 'c')
    yield from dbcleanup_wrapper(session, tmt)


@pytest.fixture
def tool_tag_association(model, session):
    tta = model.ToolTagAssociation()
    yield from dbcleanup_wrapper(session, tta)


@pytest.fixture
def transfer_job(model, session):
    tj = model.TransferJob()
    yield from dbcleanup_wrapper(session, tj)


@pytest.fixture
def user(model, session):
    u = model.User(email='test@example.com', password='password')
    yield from dbcleanup_wrapper(session, u)


@pytest.fixture
def user_authnz_token(model, session, user):
    t = model.UserAuthnzToken('a', 'b', 'c', 1, 'd', user)
    yield from dbcleanup_wrapper(session, t)


@pytest.fixture
def user_quota_association(model, session):
    uqa = model.UserQuotaAssociation(None, None)
    yield from dbcleanup_wrapper(session, uqa)


@pytest.fixture
def visualization(model, session, user):
    v = model.Visualization()
    v.user = user
    yield from dbcleanup_wrapper(session, v)


@pytest.fixture
def visualization_tag_association(model, session):
    vta = model.VisualizationTagAssociation()
    yield from dbcleanup_wrapper(session, vta)


@pytest.fixture
def workflow(model, session):
    w = model.Workflow()
    yield from dbcleanup_wrapper(session, w)


@pytest.fixture
def workflow_invocation(model, session, workflow):
    wi = model.WorkflowInvocation()
    wi.workflow = workflow
    yield from dbcleanup_wrapper(session, wi)


@pytest.fixture
def workflow_step(model, session, workflow):
    s = model.WorkflowStep()
    s.workflow = workflow
    yield from dbcleanup_wrapper(session, s)


@pytest.fixture
def workflow_step_tag_association(model, session):
    wsta = model.WorkflowStepTagAssociation()
    yield from dbcleanup_wrapper(session, wsta)


def dbcleanup_wrapper(session, obj):
    with dbcleanup(session, obj):
        yield obj


@contextmanager
def dbcleanup(session, obj, where_clause=None):
    """
    Use the session to store obj in database; delete from database on exit, bypassing the session.

    If obj does not have an id field, a SQLAlchemy WHERE clause should be provided to construct
    a custom select statement.
    """
    return_id = where_clause is None

    try:
        obj_id = persist(session, obj, return_id)
        yield obj_id
    finally:
        table = obj.__table__
        if where_clause is None:
            where_clause = get_default_where_clause(type(obj), obj_id)
        stmt = delete(table).where(where_clause)
        session.execute(stmt)


def persist(session, obj, return_id=True):
    """
    Use the session to store obj in database, then remove obj from session,
    so that on a subsequent load from the database we get a clean instance.
    """
    session.add(obj)
    session.flush()
    obj_id = obj.id if return_id else None  # save this before obj is expunged
    session.expunge(obj)
    return obj_id


def delete_from_database(session, objects):
    """
    Delete each object in objects from database.
    May be called at the end of a test if use of a context manager is impractical.
    (Assume all objects have the id field as their primary key.)
    """
    for obj in objects:
        table = obj.__table__
        stmt = delete(table).where(table.c.id == obj.id)
        session.execute(stmt)


def get_stored_obj(session, cls, obj_id=None, where_clause=None):
    # Either obj_id or where_clause must be provided, but not both
    assert bool(obj_id) ^ (where_clause is not None)
    if where_clause is None:
        where_clause = get_default_where_clause(cls, obj_id)
    stmt = select(cls).where(where_clause)
    return session.execute(stmt).scalar_one()


def get_default_where_clause(cls, obj_id):
    where_clause = cls.__table__.c.id == obj_id
    return where_clause


def has_unique_constraint(table, fields):
    for constraint in table.constraints:
        if isinstance(constraint, UniqueConstraint):
            col_names = {c.name for c in constraint.columns}
            if set(fields) == col_names:
                return True


def has_index(table, fields):
    for index in table.indexes:
        col_names = {c.name for c in index.columns}
        if set(fields) == col_names:
            return True


def get_random_string():
    """Generate unique values to accommodate unique constraints."""
    return str(random.random())
