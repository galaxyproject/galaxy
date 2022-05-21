"""
This module contains tests for column- and relationship-mapped attributes of
models, table names, as well as table-level indexes and constraints. These
tests do not address any business logic defined in the model.

Tests are grouped into classes, one for each model (tests do NOT share class instances:
https://docs.pytest.org/en/6.2.x/getting-started.html#group-multiple-tests-in-a-class)


Example of a simple model and its tests:

class Planet(Base):
    __tablename__ = 'planet'
    __table_args__ = (Index('index_name', 'name'),)

    id = Column(Integer, primary_key=True)
    name = Column(String)
    star_id = Column(Integer, ForeignKey('star.id'))

    star = relationship('Star')
    satellites = relationship('Satellite')

    def __init__(self, name):
        self.name = name


class TestPlanet(BaseTest):  # BaseTest is a base class; we need it to get the type of the model under test

    # test table name and table-level indexes and constraints
    def test_table(self, cls_):  # cls_ is a fixture defined in BaseTest, returns the type under test.
        assert cls_.__tablename__ == 'planet'  # verify table name
        assert has_index(cls.__table__, ('name',))  # verify index; second arg is a tuple containg field names

    # test column-mapped fields
    def test_columns(self, session, cls_, star):  # star is a fixture that provides a persisted instance of Star
        name = 'Saturn'  # create test values
        obj = cls_(name=name)  # pass test values to constructor
        obj.star = star  # assign test values to obj if can't pass to constructor

        with dbcleanup(session, obj) as obj_id:  # use context manager to ensure obj is deleted from db on exit.
            stored_obj = get_stored_obj(session, cls_, obj_id)  # retrieve data from db and create new obj.
            # check ALL column-mapped fields
            assert stored_obj.id == obj_id
            assert stored_obj.name == name
            assert stored_obj.star_id == star.id  # test the column attribute star_id

    # test relationship-mapped fields
    def test_relationships(self, session, cls_, star, satellite):  # satellite is a fixture for Satellite
        obj = cls_(name=name)  # use minimal possible constructor
        obj.star = star  # assign test values to test relationship-mapped attributes (not passed to constructor)
        obj.satellites.append(satellite)  # add a related object

        with dbcleanup(session, obj) as obj_id:  # same as in previous test: store, then retrieve
            stored_obj = get_stored_obj(session, cls_, obj_id)
            # check ALL relationship-mapped fields
            assert stored_obj.star.id == star.id  # test the relationship attribute star.id  (note the dot operator)
            assert collection_consists_of_objects(stored_obj.satellites, satellite)  # verify collecion of related objects


See other model tests in this module for examples of more complex setups.
"""

from datetime import timedelta
from uuid import (
    UUID,
    uuid4,
)

import pytest
from sqlalchemy import (
    func,
    select,
)

from galaxy import model
from galaxy.model.orm.now import now
from galaxy.model.orm.util import add_object_to_object_session
from .testing_utils import (
    AbstractBaseTest,
    collection_consists_of_objects,
    get_unique_value,
    has_index,
    has_unique_constraint,
)
from ..testing_utils import (
    dbcleanup,
    delete_from_database,
    get_plugin_full_name,
    get_stored_obj,
    persist,
)

model_fixtures = get_plugin_full_name("mapping.testing_utils.gxy_model_fixtures")
pytest_plugins = [model_fixtures]


class BaseTest(AbstractBaseTest):
    def get_model(self):
        return model


class TestAPIKeys(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "api_keys"

    def test_columns(self, session, cls_, user):
        create_time, user_id, key = now(), user.id, get_unique_value()
        obj = cls_(user_id=user_id, key=key, create_time=create_time)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.user_id == user_id
            assert stored_obj.key == key

    def test_relationships(self, session, cls_, user):
        obj = cls_(user_id=user.id, key=get_unique_value())

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.user.id == user.id


class TestCleanupEvent(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "cleanup_event"

    def test_columns(self, session, cls_):
        create_time, message = now(), "a"
        obj = cls_(create_time=create_time, message=message)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.message == message


class TestCleanupEventDatasetAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "cleanup_event_dataset_association"

    def test_columns(self, session, cls_, cleanup_event, dataset):
        create_time = now()
        obj = cls_(
            create_time=create_time,
            cleanup_event_id=cleanup_event.id,
            dataset_id=dataset.id,
        )

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.cleanup_event_id == cleanup_event.id
            assert stored_obj.dataset_id == dataset.id


class TestCleanupEventHistoryAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "cleanup_event_history_association"

    def test_columns(self, session, cls_, cleanup_event, history):
        create_time = now()
        obj = cls_(
            create_time=create_time,
            cleanup_event_id=cleanup_event.id,
            history_id=history.id,
        )

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.cleanup_event_id == cleanup_event.id
            assert stored_obj.history_id == history.id


class TestCleanupEventHistoryDatasetAssociationAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "cleanup_event_hda_association"

    def test_columns(self, session, cls_, cleanup_event, history_dataset_association):
        create_time = now()
        obj = cls_(
            create_time=create_time,
            cleanup_event_id=cleanup_event.id,
            hda_id=history_dataset_association.id,
        )

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.cleanup_event_id == cleanup_event.id
            assert stored_obj.hda_id == history_dataset_association.id


class TestCleanupEventImplicitlyConvertedDatasetAssociationAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "cleanup_event_icda_association"

    def test_columns(self, session, cls_, cleanup_event, implicitly_converted_dataset_association):
        create_time = now()
        obj = cls_(
            create_time=create_time,
            cleanup_event_id=cleanup_event.id,
            icda_id=implicitly_converted_dataset_association.id,
        )

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.cleanup_event_id == cleanup_event.id
            assert stored_obj.icda_id == implicitly_converted_dataset_association.id


class TestCleanupEventLibraryAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "cleanup_event_library_association"

    def test_columns(self, session, cls_, cleanup_event, library):
        create_time = now()
        obj = cls_(
            create_time=create_time,
            cleanup_event_id=cleanup_event.id,
            library_id=library.id,
        )

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.cleanup_event_id == cleanup_event.id
            assert stored_obj.library_id == library.id


class TestCleanupEventLibraryDatasetAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "cleanup_event_library_dataset_association"

    def test_columns(self, session, cls_, cleanup_event, library_dataset):
        create_time = now()
        obj = cls_(
            create_time=create_time,
            cleanup_event_id=cleanup_event.id,
            library_dataset_id=library_dataset.id,
        )

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.cleanup_event_id == cleanup_event.id
            assert stored_obj.library_dataset_id == library_dataset.id


class TestCleanupEventLibraryDatasetDatasetAssociationAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "cleanup_event_ldda_association"

    def test_columns(self, session, cls_, cleanup_event, library_dataset_dataset_association):
        create_time = now()
        obj = cls_(
            create_time=create_time,
            cleanup_event_id=cleanup_event.id,
            ldda_id=library_dataset_dataset_association.id,
        )

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.cleanup_event_id == cleanup_event.id
            assert stored_obj.ldda_id == library_dataset_dataset_association.id


class TestCleanupEventLibraryFolderAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "cleanup_event_library_folder_association"

    def test_columns(self, session, cls_, cleanup_event, library_folder):
        create_time = now()
        obj = cls_(
            create_time=create_time,
            cleanup_event_id=cleanup_event.id,
            library_folder_id=library_folder.id,
        )

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.cleanup_event_id == cleanup_event.id
            assert stored_obj.library_folder_id == library_folder.id


class TestCleanupEventMetadataFileAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "cleanup_event_metadata_file_association"

    def test_columns(self, session, cls_, cleanup_event, metadata_file):
        create_time = now()
        obj = cls_(
            create_time=create_time,
            cleanup_event_id=cleanup_event.id,
            metadata_file_id=metadata_file.id,
        )
        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.cleanup_event_id == cleanup_event.id
            assert stored_obj.metadata_file_id == metadata_file.id


class TestCustosAuthnzToken(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "custos_authnz_token"
        assert has_unique_constraint(cls_.__table__, ("user_id", "external_user_id", "provider"))
        assert has_unique_constraint(cls_.__table__, ("external_user_id", "provider"))

    def test_columns(self, session, cls_, user):
        external_user_id = "a"
        provider = "b"
        access_token = "c"
        id_token = "d"
        refresh_token = "e"
        expiration_time = now()
        refresh_expiration_time = expiration_time + timedelta(hours=1)

        obj = cls_()
        obj.user = user
        obj.external_user_id = external_user_id
        obj.provider = provider
        obj.access_token = access_token
        obj.id_token = id_token
        obj.refresh_token = refresh_token
        obj.expiration_time = expiration_time
        obj.refresh_expiration_time = refresh_expiration_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.user_id == user.id
            assert stored_obj.external_user_id == external_user_id
            assert stored_obj.provider == provider
            assert stored_obj.access_token == access_token
            assert stored_obj.id_token == id_token
            assert stored_obj.refresh_token == refresh_token
            assert stored_obj.expiration_time == expiration_time
            assert stored_obj.refresh_expiration_time == refresh_expiration_time

    def test_relationships(self, session, cls_, user):
        obj = cls_()
        obj.user = user

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.user.id == user.id


class TestCloudAuthz(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "cloudauthz"

    def test_columns(self, session, cls_, user, user_authnz_token):
        provider, config, description = "a", "b", "c"
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
        obj = cls_(user.id, None, None, user_authnz_token.id, "c")

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.user.id == user.id
            assert stored_obj.authn.id == user_authnz_token.id


class TestDataManagerHistoryAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "data_manager_history_association"

    def test_columns(self, session, cls_, history, user):
        create_time = now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.history = history
        obj.user = user

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
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


class TestDataManagerJobAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "data_manager_job_association"
        assert has_index(cls_.__table__, ("data_manager_id",))

    def test_columns(self, session, cls_, job):
        create_time = now()
        update_time = create_time + timedelta(hours=1)
        data_manager_id = "a"
        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.job = job
        obj.data_manager_id = data_manager_id

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.job_id == job.id
            assert stored_obj.data_manager_id == data_manager_id

    def test_relationships(self, session, cls_, job):
        obj = cls_(job=job)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id


class TestDataset(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "dataset"

    def test_columns(self, session, cls_, job):
        create_time = now()
        update_time = create_time + timedelta(hours=1)
        state = "a"
        deleted = True
        purged = True
        purgable = False
        object_store_id = "b"
        external_filename = "c"
        _extra_files_path = "d"
        created_from_basename = "e"
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
        history_dataset_association_factory,
    ):
        obj = cls_()
        obj.job = job
        obj.actions.append(dataset_permission)
        obj.history_associations.append(history_dataset_association)
        obj.library_associations.append(library_dataset_dataset_association)
        obj.hashes.append(dataset_hash)
        obj.sources.append(dataset_source)

        hda = history_dataset_association_factory()
        hda.purged = True
        obj.history_associations.append(hda)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id
            assert collection_consists_of_objects(stored_obj.actions, dataset_permission)
            assert collection_consists_of_objects(stored_obj.active_history_associations, history_dataset_association)
            assert stored_obj.purged_history_associations[0].id == hda.id
            assert collection_consists_of_objects(
                stored_obj.active_library_associations,
                library_dataset_dataset_association,
            )
            assert collection_consists_of_objects(stored_obj.hashes, dataset_hash)
            assert collection_consists_of_objects(stored_obj.sources, dataset_source)
            assert collection_consists_of_objects(stored_obj.library_associations, library_dataset_dataset_association)
            assert collection_consists_of_objects(stored_obj.history_associations, hda, history_dataset_association)

        delete_from_database(session, hda)


class TestDatasetCollection(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "dataset_collection"

    def test_columns(self, session, cls_):
        collection_type = "a"
        populated_state = "b"
        populated_state_message = "c"
        element_count = 1
        create_time = now()
        update_time = create_time + timedelta(hours=1)

        obj = cls_()
        obj.collection_type = collection_type
        obj.populated_state = populated_state
        obj.populated_state_message = populated_state_message
        obj.element_count = element_count
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.collection_type == collection_type
            assert stored_obj.populated_state == populated_state
            assert stored_obj.populated_state_message == populated_state_message
            assert stored_obj.element_count == element_count
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time

    def test_relationships(
        self,
        session,
        cls_,
        dataset_collection_element,
    ):
        obj = cls_()
        obj.collection_type, obj.populated_state = "a", "b"
        obj.elements.append(dataset_collection_element)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert collection_consists_of_objects(stored_obj.elements, dataset_collection_element)


class TestDatasetCollectionElement(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "dataset_collection_element"

    def test_columns(
        self,
        session,
        cls_,
        dataset_collection,
        history_dataset_association,
        library_dataset_dataset_association,
        dataset_collection_factory,
    ):
        element_index, element_identifier = 1, "a"
        obj = cls_(element=history_dataset_association)  # using hda is sufficient for this test
        obj.element_index = element_index
        obj.element_identifier = element_identifier
        obj.hda = history_dataset_association
        obj.ldda = library_dataset_dataset_association
        obj.child_collection = dataset_collection

        # set dataset_collection_id (can't set directly; persisted automatically)
        parent_collection = dataset_collection_factory()
        parent_collection.elements.append(obj)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.dataset_collection_id == parent_collection.id
            assert stored_obj.hda_id == history_dataset_association.id
            assert stored_obj.ldda_id == library_dataset_dataset_association.id
            assert stored_obj.child_collection_id == dataset_collection.id
            assert stored_obj.element_index == element_index
            assert stored_obj.element_identifier == element_identifier

        delete_from_database(session, parent_collection)

    def test_relationships(
        self,
        session,
        cls_,
        dataset_collection,
        history_dataset_association,
        library_dataset_dataset_association,
        dataset_collection_factory,
    ):
        obj = cls_(element=history_dataset_association)  # using hda is sufficient for this test
        obj.hda = history_dataset_association
        obj.ldda = library_dataset_dataset_association
        obj.child_collection = dataset_collection

        parent_collection = dataset_collection_factory()
        obj.collection = parent_collection  # same as parent_collection.elements.append(obj)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.hda.id == history_dataset_association.id
            assert stored_obj.ldda.id == library_dataset_dataset_association.id
            assert stored_obj.child_collection.id == dataset_collection.id
            assert stored_obj.collection.id == parent_collection.id

        delete_from_database(session, parent_collection)


class TestDatasetHash(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "dataset_hash"

    def test_columns(self, session, cls_, dataset):
        hash_function, hash_value, extra_files_path = "a", "b", "c"
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


class TestDatasetPermissions(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "dataset_permissions"

    def test_columns(self, session, cls_, dataset, role):
        action = "a"
        create_time = now()
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


class TestDatasetSource(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "dataset_source"

    def test_columns(self, session, cls_, dataset):
        source_uri, extra_files_path, transform = "a", "b", "c"
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
            assert collection_consists_of_objects(stored_obj.hashes, dataset_source_hash)


class TestDatasetSourceHash(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "dataset_source_hash"

    def test_columns(self, session, cls_, dataset_source):
        hash_function, hash_value = "a", "b"
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


class TestDefaultHistoryPermissions(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "default_history_permissions"

    def test_columns(self, session, cls_, history, role):
        action = "a"
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
        assert cls_.__tablename__ == "default_quota_association"

    def test_columns(self, session, cls_, quota):
        type_ = cls_.types.REGISTERED
        create_time = now()
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
        assert cls_.__tablename__ == "default_user_permissions"

    def test_columns(self, session, cls_, user, role):
        action = "a"
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


class TestDynamicTool(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "dynamic_tool"

    def test_columns(self, session, cls_):
        tool_format = "a"
        tool_id = "b"
        tool_version = "c"
        tool_path = "d"
        tool_directory = "e"
        uuid = uuid4()
        active = True
        hidden = True
        value = "f"
        create_time = now()
        update_time = create_time + timedelta(hours=1)

        obj = cls_()
        obj.tool_format = tool_format
        obj.tool_id = tool_id
        obj.tool_version = tool_version
        obj.tool_path = tool_path
        obj.tool_directory = tool_directory
        obj.uuid = uuid
        obj.active = active
        obj.hidden = hidden
        obj.value = value
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.uuid == uuid
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

    def test_construct_with_uuid(self, session, cls_):
        uuid = uuid4()
        obj = cls_(uuid=uuid)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.uuid == uuid

    def test_construct_without_uuid(self, session, cls_):
        obj = cls_()

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert isinstance(stored_obj.uuid, UUID)


class TestEvent(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "event"

    def test_columns(self, session, cls_, history, galaxy_session, user):
        message, tool_id = "a", "b"
        create_time = now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_()
        obj.message = message
        obj.history = history
        obj.user = user
        obj.galaxy_session = galaxy_session
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
        obj = cls_()
        obj.history = history
        obj.user = user
        obj.galaxy_session = galaxy_session

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.history.id == history.id
            assert stored_obj.user.id == user.id
            assert stored_obj.galaxy_session.id == galaxy_session.id


class TestExtendedMetadata(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "extended_metadata"

    def test_columns(self, session, cls_):
        data = "a"
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
            assert collection_consists_of_objects(stored_obj.children, extended_metadata_index)


class TestExtendedMetadataIndex(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "extended_metadata_index"

    def test_columns(self, session, cls_, extended_metadata):
        path, value = "a", "b"
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
        assert cls_.__tablename__ == "form_definition"

    def test_columns(self, session, cls_, form_definition_current):
        name, desc, fields, type, layout = "a", "b", "c", "d", "e"
        create_time = now()
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
        obj = cls_(name="a", form_definition_current=form_definition_current)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.form_definition_current.id == form_definition_current.id


class TestFormDefinitionCurrent(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "form_definition_current"

    def test_columns(self, session, cls_, form_definition):
        create_time = now()
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
            assert collection_consists_of_objects(stored_obj.forms, form_definition)


class TestFormValues(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "form_values"

    def test_columns(self, session, cls_, form_definition):
        content = "a"
        create_time = now()
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
        assert cls_.__tablename__ == "galaxy_session"

    def test_columns(self, session, cls_, user, history, galaxy_session):

        create_time = now()
        update_time = create_time + timedelta(hours=1)
        remote_host = "a"
        remote_addr = "b"
        referer = "c"
        session_key = get_unique_value()
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
        obj.session_key = get_unique_value()
        obj.histories.append(galaxy_session_history_association)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.user.id == user.id
            assert stored_obj.current_history.id == history.id
            assert collection_consists_of_objects(stored_obj.histories, galaxy_session_history_association)


class TestGalaxySessionToHistoryAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "galaxy_session_to_history"

    def test_columns(self, session, cls_, galaxy_session, history):
        create_time = now()
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
        assert cls_.__tablename__ == "genome_index_tool_data"

    def test_columns(self, session, cls_, job, dataset, user):
        fasta_path = "a"
        created_time = now()
        modified_time = created_time + timedelta(hours=1)
        indexer = "b"
        obj = cls_()
        obj.job = job
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
            assert stored_obj.dataset_id == dataset.id
            assert stored_obj.fasta_path == fasta_path
            assert stored_obj.created_time == created_time
            assert stored_obj.modified_time == modified_time
            assert stored_obj.indexer == indexer
            assert stored_obj.user_id == user.id

    def test_relationships(self, session, cls_, job, dataset, user):
        obj = cls_()
        obj.job = job
        obj.dataset = dataset
        obj.user = user

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id
            assert stored_obj.dataset.id == dataset.id
            assert stored_obj.user.id == user.id


class TestGroup(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "galaxy_group"

    def test_columns(self, session, cls_):
        create_time = now()
        update_time = create_time + timedelta(hours=1)
        name = get_unique_value()
        deleted = True

        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.name = name
        obj.deleted = deleted

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.name == name
            assert stored_obj.deleted == deleted

    def test_relationships(
        self,
        session,
        cls_,
        group_quota_association,
        group_role_association,
        user_group_association,
    ):
        obj = cls_(name=get_unique_value())
        obj.quotas.append(group_quota_association)
        obj.roles.append(group_role_association)
        obj.users.append(user_group_association)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert collection_consists_of_objects(stored_obj.quotas, group_quota_association)
            assert collection_consists_of_objects(stored_obj.roles, group_role_association)
            assert collection_consists_of_objects(stored_obj.users, user_group_association)


class TestGroupQuotaAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "group_quota_association"

    def test_columns(self, session, cls_, group, quota):
        create_time = now()
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
        assert cls_.__tablename__ == "group_role_association"

    def test_columns(self, session, cls_, group, role):
        obj = cls_(group, role)
        create_time = now()
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
        assert cls_.__tablename__ == "history"
        assert has_index(cls_.__table__, ("slug",))

    def test_columns(self, session, cls_, user):
        create_time = now()
        name = "a"
        hid_counter = 2
        deleted = True
        purged = True
        importing = True
        genome_build = "b"
        importable = True
        slug = "c"
        published = True
        obj = cls_(name=name, user=user)
        obj.create_time = create_time
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
            # Can't test: populated via trigger; n/a in this test setup (applies to column and column property)
            assert stored_obj.update_time is None
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
        workflow_invocation,
        job,
    ):
        obj = cls_(user=user)
        obj.datasets.append(history_dataset_association)
        obj.dataset_collections.append(history_dataset_collection_association)
        obj.exports.append(job_export_history_archive)
        obj.tags.append(history_tag_association)
        obj.annotations.append(history_annotation_association)
        obj.ratings.append(history_rating_association)
        obj.default_permissions.append(default_history_permissions)
        obj.users_shared_with.append(history_user_share_association)
        obj.galaxy_sessions.append(galaxy_session_history_association)
        obj.workflow_invocations.append(workflow_invocation)
        obj.jobs.append(job)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.user.id == user.id
            assert collection_consists_of_objects(stored_obj.datasets, history_dataset_association)
            assert collection_consists_of_objects(stored_obj.exports, job_export_history_archive)
            assert collection_consists_of_objects(stored_obj.active_datasets, history_dataset_association)
            assert collection_consists_of_objects(
                stored_obj.active_dataset_collections,
                history_dataset_collection_association,
            )
            assert collection_consists_of_objects(stored_obj.visible_datasets, history_dataset_association)
            assert collection_consists_of_objects(
                stored_obj.visible_dataset_collections,
                history_dataset_collection_association,
            )
            assert collection_consists_of_objects(stored_obj.tags, history_tag_association)
            assert collection_consists_of_objects(stored_obj.annotations, history_annotation_association)
            assert collection_consists_of_objects(stored_obj.ratings, history_rating_association)
            # This doesn't test the average amount, just the mapping.
            assert stored_obj.average_rating == history_rating_association.rating
            assert stored_obj.users_shared_with_count == 1
            assert collection_consists_of_objects(stored_obj.users_shared_with, history_user_share_association)
            assert collection_consists_of_objects(stored_obj.default_permissions, default_history_permissions)
            assert collection_consists_of_objects(stored_obj.galaxy_sessions, galaxy_session_history_association)
            assert collection_consists_of_objects(stored_obj.workflow_invocations, workflow_invocation)
            assert collection_consists_of_objects(stored_obj.jobs, job)

    def test_average_rating(self, session, history, user, history_rating_association_factory):
        _run_average_rating_test(session, history, user, history_rating_association_factory)


class TestHistoryAnnotationAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "history_annotation_association"
        assert has_index(cls_.__table__, ("annotation",))

    def test_columns(self, session, cls_, history, user):
        annotation = "a"
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


class TestHistoryDatasetAssociation(BaseTest):
    def test_table(self, cls_):
        # mapped imperatively, so do not test cls_.__tablename__
        assert cls_.table.name == "history_dataset_association"

    def test_columns(
        self,
        session,
        cls_,
        history,
        dataset,
        library_dataset_dataset_association,
        extended_metadata,
        history_dataset_collection_association,
        history_dataset_association_factory,
    ):
        copied_from_hda = history_dataset_association_factory()
        parent = history_dataset_association_factory()

        create_time = now()
        update_time = create_time + timedelta(hours=1)
        state = "a"
        name = "b"
        info = "c"
        blurb = "d"
        peek = "e"
        tool_version = "f"
        extension = "g"
        _metadata = {"key": "value"}
        designation = "i"
        deleted = False
        visible = False
        version = 1
        hid = 2
        purged = False
        validated_state = "j"
        validated_state_message = "k"

        obj = cls_()
        obj.history = history
        obj.dataset = dataset
        obj.create_time = create_time
        obj.update_time = update_time
        obj.state = state
        obj.copied_from_history_dataset_association = copied_from_hda
        obj.copied_from_library_dataset_dataset_association = library_dataset_dataset_association
        obj.name = name
        obj.info = info
        obj.blurb = blurb
        obj.peek = peek
        obj.tool_version = tool_version
        obj.extension = extension
        obj._metadata = _metadata
        obj.parent_id = parent.id
        obj.designation = designation
        obj.deleted = deleted
        obj.visible = visible
        obj.extended_metadata = extended_metadata
        obj.version = version
        obj.hid = hid
        obj.purged = purged
        obj.validated_state = validated_state
        obj.validated_state_message = validated_state_message
        obj.hidden_beneath_collection_instance = history_dataset_collection_association

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.history_id == history.id
            assert stored_obj.dataset_id == dataset.id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.state == state
            assert stored_obj.copied_from_history_dataset_association_id == copied_from_hda.id
            assert (
                stored_obj.copied_from_library_dataset_dataset_association_id == library_dataset_dataset_association.id
            )
            assert stored_obj.name == name
            assert stored_obj.info == info
            assert stored_obj.blurb == blurb
            assert stored_obj.peek == peek
            assert stored_obj.tool_version == tool_version
            assert stored_obj.extension == extension
            assert stored_obj._metadata == _metadata
            assert stored_obj.parent_id == parent.id
            assert stored_obj.designation == designation
            assert stored_obj.deleted == deleted
            assert stored_obj.visible == visible
            assert stored_obj.extended_metadata_id == extended_metadata.id
            assert stored_obj.version == version
            assert stored_obj.hid == hid
            assert stored_obj.purged == purged
            assert stored_obj.validated_state == validated_state
            assert stored_obj.validated_state_message == validated_state_message
            assert stored_obj.hidden_beneath_collection_instance_id == history_dataset_collection_association.id

        delete_from_database(session, [copied_from_hda, parent])

    def test_detached_histories(
        self,
        session,
        history,
    ):
        hda = model.HistoryDatasetAssociation(create_dataset=False)
        assert hda not in session
        session.add(history)
        assert history in session
        hda.history = history
        assert hda not in session

    def test_relationships(
        self,
        session,
        cls_,
        history,
        dataset,
        extended_metadata,
        history_dataset_collection_association,
        history_dataset_association_factory,
        history_dataset_association_tag_association,
        history_dataset_association_annotation_association,
        history_dataset_association_rating_association,
        job_to_input_dataset_association,
        job_to_output_dataset_association,
        implicitly_converted_dataset_association_factory,
        library_dataset_dataset_association_factory,
    ):
        copied_from_hda = history_dataset_association_factory()
        copied_to_hda = history_dataset_association_factory()
        copied_from_ldda = library_dataset_dataset_association_factory()
        copied_to_ldda = library_dataset_dataset_association_factory()
        icda = implicitly_converted_dataset_association_factory()
        icpda = implicitly_converted_dataset_association_factory()
        persisted = [
            copied_from_hda,
            copied_to_hda,
            copied_from_ldda,
            copied_to_ldda,
            icda,
            icpda,
        ]

        obj = cls_(dataset=dataset)
        obj.history = history
        obj.copied_from_history_dataset_association = copied_from_hda
        obj.copied_from_library_dataset_dataset_association = copied_from_ldda
        obj.extended_metadata = extended_metadata
        obj.validated_state = "a"
        obj.hidden_beneath_collection_instance = history_dataset_collection_association
        obj.copied_to_library_dataset_dataset_associations.append(copied_to_ldda)
        obj.copied_to_history_dataset_associations.append(copied_to_hda)
        obj.tags.append(history_dataset_association_tag_association)
        obj.annotations.append(history_dataset_association_annotation_association)
        obj.ratings.append(history_dataset_association_rating_association)
        obj.dependent_jobs.append(job_to_input_dataset_association)
        obj.creating_job_associations.append(job_to_output_dataset_association)
        obj.implicitly_converted_datasets.append(icda)
        obj.implicitly_converted_parent_datasets.append(icpda)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.history.id == history.id
            assert stored_obj.dataset.id == dataset.id
            assert stored_obj.copied_from_history_dataset_association.id == copied_from_hda.id
            assert stored_obj.copied_from_library_dataset_dataset_association.id == copied_from_ldda.id
            assert stored_obj.extended_metadata.id == extended_metadata.id
            assert stored_obj.hidden_beneath_collection_instance.id == history_dataset_collection_association.id
            assert collection_consists_of_objects(
                stored_obj.copied_to_library_dataset_dataset_associations,
                copied_to_ldda,
            )
            assert collection_consists_of_objects(stored_obj.copied_to_history_dataset_associations, copied_to_hda)
            assert collection_consists_of_objects(stored_obj.tags, history_dataset_association_tag_association)
            assert collection_consists_of_objects(
                stored_obj.annotations,
                history_dataset_association_annotation_association,
            )
            assert collection_consists_of_objects(stored_obj.ratings, history_dataset_association_rating_association)
            assert collection_consists_of_objects(stored_obj.dependent_jobs, job_to_input_dataset_association)
            assert collection_consists_of_objects(
                stored_obj.creating_job_associations, job_to_output_dataset_association
            )
            assert collection_consists_of_objects(stored_obj.implicitly_converted_datasets, icda)
            assert collection_consists_of_objects(stored_obj.implicitly_converted_parent_datasets, icpda)

        delete_from_database(session, persisted)


class TestHistoryDatasetAssociationAnnotationAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "history_dataset_association_annotation_association"
        assert has_index(cls_.__table__, ("annotation",))

    def test_columns(self, session, cls_, history_dataset_association, user):
        annotation = "a"
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
        assert cls_.__tablename__ == "history_dataset_association_display_at_authorization"

    def test_columns(self, session, cls_, history_dataset_association, user):
        create_time = now()
        update_time = create_time + timedelta(hours=1)
        site = "a"
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


class TestHistoryDatasetAssociationHistory(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "history_dataset_association_history"

    def test_columns(self, session, cls_, history_dataset_association, extended_metadata):
        name, update_time, version, extension, metadata = (
            "a",
            now(),
            2,
            "b",
            {"key": "value"},
        )
        obj = cls_(
            history_dataset_association.id,
            name,
            None,
            update_time,
            version,
            extension,
            extended_metadata.id,
            metadata,
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


class TestHistoryDatasetAssociationRatingAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "history_dataset_association_rating_association"

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


class TestHistoryDatasetAssociationSubset(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "history_dataset_association_subset"

    def test_columns(
        self,
        session,
        cls_,
        history_dataset_association,
        history_dataset_association_factory,
    ):
        hda_subset = history_dataset_association_factory()
        persist(session, hda_subset)

        location = "a"
        obj = cls_(history_dataset_association, hda_subset, location)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.history_dataset_association_id == history_dataset_association.id
            assert stored_obj.history_dataset_association_subset_id == hda_subset.id
            assert stored_obj.location == location

        delete_from_database(session, hda_subset)

    def test_relationships(
        self,
        session,
        cls_,
        history_dataset_association,
        history_dataset_association_factory,
    ):
        hda_subset = history_dataset_association_factory()
        persist(session, hda_subset)

        obj = cls_(history_dataset_association, hda_subset, None)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.hda.id == history_dataset_association.id
            assert stored_obj.subset.id == hda_subset.id

        delete_from_database(session, hda_subset)


class TestHistoryDatasetAssociationTagAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "history_dataset_association_tag_association"

    def test_columns(self, session, cls_, history_dataset_association, tag, user):
        user_tname, value, user_value = "a", "b", "c"
        obj = cls_(
            user=user,
            tag=tag,
            user_tname=user_tname,
            value=value,
            user_value=user_value,
        )
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


class TestHistoryDatasetCollectionAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "history_dataset_collection_association"

    def test_columns(
        self,
        session,
        cls_,
        dataset_collection,
        history,
        history_dataset_collection_association,
        job,
        implicit_collection_jobs,
    ):
        name = "a"
        hid = 1
        visible = True
        deleted = True
        implicit_output_name = "b"
        create_time = now()
        update_time = create_time + timedelta(hours=1)

        obj = cls_()
        obj.collection = dataset_collection
        obj.history = history
        obj.name = name
        obj.hid = hid
        obj.visible = visible
        obj.deleted = deleted
        obj.copied_from_history_dataset_collection_association = history_dataset_collection_association
        obj.implicit_output_name = implicit_output_name
        obj.job = job
        obj.implicit_collection_jobs = implicit_collection_jobs
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.collection_id == dataset_collection.id
            assert stored_obj.history_id == history.id
            assert stored_obj.name == name
            assert stored_obj.hid == hid
            assert stored_obj.visible == visible
            assert stored_obj.deleted == deleted
            assert (
                stored_obj.copied_from_history_dataset_collection_association_id
                == history_dataset_collection_association.id
            )
            assert stored_obj.implicit_output_name == implicit_output_name
            assert stored_obj.job_id == job.id
            assert stored_obj.implicit_collection_jobs_id == implicit_collection_jobs.id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time

    def test_relationships(
        self,
        session,
        cls_,
        dataset_collection,
        history,
        history_dataset_collection_association,
        history_dataset_collection_association_factory,
        job,
        implicit_collection_jobs,
        implicitly_created_dataset_collection_input,
        history_dataset_collection_annotation_association,
        history_dataset_collection_rating_association,
        history_dataset_collection_tag_association,
        job_to_output_dataset_collection_association,
    ):
        copied_to_hdca = history_dataset_collection_association_factory()

        obj = cls_()
        obj.collection = dataset_collection
        obj.history = history
        add_object_to_object_session(obj, history_dataset_collection_association)
        obj.copied_from_history_dataset_collection_association = history_dataset_collection_association
        obj.copied_to_history_dataset_collection_association.append(copied_to_hdca)
        obj.job = job
        obj.implicit_collection_jobs = implicit_collection_jobs
        obj.implicit_input_collections.append(implicitly_created_dataset_collection_input)
        obj.tags.append(history_dataset_collection_tag_association)
        obj.annotations.append(history_dataset_collection_annotation_association)
        obj.ratings.append(history_dataset_collection_rating_association)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.collection.id == dataset_collection.id
            assert stored_obj.history.id == history.id
            assert (
                stored_obj.copied_from_history_dataset_collection_association.id
                == history_dataset_collection_association.id
            )
            assert collection_consists_of_objects(
                stored_obj.copied_to_history_dataset_collection_association,
                copied_to_hdca,
            )
            assert stored_obj.job.id == job.id
            assert stored_obj.implicit_collection_jobs.id == implicit_collection_jobs.id
            assert collection_consists_of_objects(
                stored_obj.implicit_input_collections,
                implicitly_created_dataset_collection_input,
            )
            assert collection_consists_of_objects(stored_obj.tags, history_dataset_collection_tag_association)
            assert collection_consists_of_objects(
                stored_obj.annotations,
                history_dataset_collection_annotation_association,
            )
            assert collection_consists_of_objects(stored_obj.ratings, history_dataset_collection_rating_association)
            # stored_obj.job_state_summary is a view: can't test in this setup.

        delete_from_database(session, copied_to_hdca)


class TestHistoryDatasetCollectionAssociationAnnotationAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "history_dataset_collection_annotation_association"

    def test_columns(self, session, cls_, history_dataset_collection_association, user):
        annotation = "a"
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
        assert cls_.__tablename__ == "history_dataset_collection_rating_association"

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
        assert cls_.__tablename__ == "history_dataset_collection_tag_association"

    def test_columns(self, session, cls_, history_dataset_collection_association, tag, user):
        user_tname, value, user_value = "a", "b", "c"
        obj = cls_(
            user=user,
            tag=tag,
            user_tname=user_tname,
            value=value,
            user_value=user_value,
        )
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
        assert cls_.__tablename__ == "history_rating_association"

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
        assert cls_.__tablename__ == "history_tag_association"

    def test_columns(self, session, cls_, history, tag, user):
        user_tname, value, user_value = "a", "b", "c"
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


class TestHistoryUserShareAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "history_user_share_association"

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


class TestImplicitCollectionJobs(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "implicit_collection_jobs"

    def test_columns(self, session, cls_):
        populated_state = "a"
        obj = cls_()
        obj.populated_state = populated_state

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.populated_state == populated_state

    def test_relationships(
        self,
        session,
        cls_,
        implicit_collection_jobs_job_association,
    ):
        obj = cls_()
        obj.jobs.append(implicit_collection_jobs_job_association)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert collection_consists_of_objects(stored_obj.jobs, implicit_collection_jobs_job_association)


class TestImplicitCollectionJobsJobAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "implicit_collection_jobs_job_association"

    def test_columns(self, session, cls_, implicit_collection_jobs, job):
        order_index = 1
        obj = cls_()
        obj.implicit_collection_jobs = implicit_collection_jobs
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
        obj.job = job
        obj.order_index = 1

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.implicit_collection_jobs.id == implicit_collection_jobs.id
            assert stored_obj.job.id == job.id


class TestImplicitlyConvertedDatasetAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "implicitly_converted_dataset_association"

    def test_columns(
        self,
        session,
        cls_,
        history_dataset_association,
        library_dataset_dataset_association,
    ):
        create_time = now()
        update_time = create_time + timedelta(hours=1)
        deleted = True
        metadata_safe = False
        type = "a"

        # Test this combination (dataset/parent, hda/ldda); assume this is sufficient for other combinations.
        obj = cls_(
            parent=library_dataset_dataset_association,
            dataset=history_dataset_association,
        )
        obj.create_time = create_time
        obj.update_time = update_time
        obj.deleted = deleted
        obj.metadata_safe = metadata_safe
        obj.type = type

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.hda_id == history_dataset_association.id
            assert stored_obj.ldda_id is None
            assert stored_obj.hda_parent_id is None
            assert stored_obj.ldda_parent_id == library_dataset_dataset_association.id
            assert stored_obj.deleted == deleted
            assert stored_obj.metadata_safe == metadata_safe
            assert stored_obj.type == type

    def test_relationships(
        self,
        session,
        cls_,
        history_dataset_association,
        library_dataset_dataset_association,
    ):
        # Switch hda and ldda (different from test_columns() setup)
        obj = cls_(
            parent=history_dataset_association,
            dataset=library_dataset_dataset_association,
        )

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.dataset is None
            assert stored_obj.dataset_ldda.id == library_dataset_dataset_association.id
            assert stored_obj.parent_hda.id == history_dataset_association.id
            assert stored_obj.parent_ldda is None


class TestImplicitlyCreatedDatasetCollectionInput(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "implicitly_created_dataset_collection_inputs"

    def test_columns(
        self,
        session,
        cls_,
        history_dataset_collection_association,
        history_dataset_collection_association_factory,
    ):
        name = "a"

        hdca2 = history_dataset_collection_association_factory()
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

    def test_relationships(
        self,
        session,
        cls_,
        history_dataset_collection_association,
    ):
        obj = cls_(None, history_dataset_collection_association)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.input_dataset_collection.id == history_dataset_collection_association.id


class TestInteractiveToolEntryPoint(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "interactivetool_entry_point"

    def test_columns(self, session, cls_, job):
        name = "a"
        token = "b"
        tool_port = 1
        host = "c"
        port = 2
        protocol = "d"
        entry_url = "e"
        requires_domain = False
        info = "f"
        configured = True
        deleted = True
        created_time = now()
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


class TestJob(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "job"

    def test_columns(
        self,
        session,
        cls_,
        history,
        library_folder,
        dynamic_tool,
        galaxy_session,
        user,
    ):
        create_time = now()
        update_time = create_time + timedelta(hours=1)
        tool_id = "a"
        tool_version = "b"
        galaxy_version = "c"
        state = "d"
        info = "e"
        copied_from_job_id = 1
        command_line = "f"
        dependencies = "g"
        job_messages = "h"
        param_filename = "i"
        runner_name = "j"
        job_stdout = "k"
        job_stderr = "m"
        tool_stdout = "n"
        tool_stderr = "o"
        exit_code = 2
        traceback = "p"
        job_runner_name = "q"
        job_runner_external_id = "r"
        destination_id = "s"
        destination_params = "u"
        object_store_id = "v"
        imported = False
        params = "w"
        handler = "x"

        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.history = history
        obj.library_folder = library_folder
        obj.tool_id = tool_id
        obj.tool_version = tool_version
        obj.galaxy_version = galaxy_version
        obj.dynamic_tool_id = dynamic_tool.id
        obj.state = state
        obj.info = info
        obj.copied_from_job_id = copied_from_job_id
        obj.command_line = command_line
        obj.dependencies = dependencies
        obj.job_messages = job_messages
        obj.param_filename = param_filename
        obj.runner_name = runner_name
        obj.job_stdout = job_stdout
        obj.job_stderr = job_stderr
        obj.tool_stdout = tool_stdout
        obj.tool_stderr = tool_stderr
        obj.exit_code = exit_code
        obj.traceback = traceback
        obj.galaxy_session = galaxy_session
        obj.user = user
        obj.job_runner_name = job_runner_name
        obj.job_runner_external_id = job_runner_external_id
        obj.destination_id = destination_id
        obj.destination_params = destination_params
        obj.object_store_id = object_store_id
        obj.imported = imported
        obj.params = params
        obj.handler = handler

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id, unique=True)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.history_id == history.id
            assert stored_obj.library_folder_id == library_folder.id
            assert stored_obj.tool_id == tool_id
            assert stored_obj.tool_version == tool_version
            assert stored_obj.galaxy_version == galaxy_version
            assert stored_obj.dynamic_tool_id == dynamic_tool.id
            assert stored_obj.state == state
            assert stored_obj.info == info
            assert stored_obj.copied_from_job_id == copied_from_job_id
            assert stored_obj.command_line == command_line
            assert stored_obj.dependencies == dependencies
            assert stored_obj.job_messages == job_messages
            assert stored_obj.param_filename == param_filename
            assert stored_obj.runner_name == runner_name
            assert stored_obj.job_stdout == job_stdout
            assert stored_obj.job_stderr == job_stderr
            assert stored_obj.tool_stdout == tool_stdout
            assert stored_obj.tool_stderr == tool_stderr
            assert stored_obj.exit_code == exit_code
            assert stored_obj.traceback == traceback
            assert stored_obj.session_id == galaxy_session.id
            assert stored_obj.user_id == user.id
            assert stored_obj.job_runner_name == job_runner_name
            assert stored_obj.job_runner_external_id == job_runner_external_id
            assert stored_obj.destination_id == destination_id
            assert stored_obj.destination_params == destination_params
            assert stored_obj.object_store_id == object_store_id
            assert stored_obj.imported == imported
            assert stored_obj.params == params
            assert stored_obj.handler == handler

    def test_relationships(
        self,
        session,
        cls_,
        history,
        library_folder,
        dynamic_tool,
        galaxy_session,
        user,
        job_parameter,
        job_to_input_dataset_association,
        job_to_input_dataset_collection_association,
        job_to_input_dataset_collection_element_association,
        job_to_output_dataset_collection_association,
        job_to_implicit_output_dataset_collection_association,
        post_job_action_association,
        job_to_input_library_dataset_association,
        job_to_output_library_dataset_association,
        job_external_output_metadata,
        task,
        job_to_output_dataset_association,
        job_state_history,
        job_metric_text,
        job_metric_numeric,
        interactive_tool_entry_point,
        implicit_collection_jobs_job_association,
        job_container_association,
        data_manager_job_association,
        history_dataset_collection_association,
        workflow_invocation_step,
    ):
        obj = cls_()
        obj.history = history
        obj.library_folder = library_folder
        obj.galaxy_session = galaxy_session
        obj.user = user
        obj.parameters.append(job_parameter)
        obj.input_datasets.append(job_to_input_dataset_association)
        obj.input_dataset_collections.append(job_to_input_dataset_collection_association)
        obj.input_dataset_collection_elements.append(job_to_input_dataset_collection_element_association)
        obj.output_dataset_collection_instances.append(job_to_output_dataset_collection_association)
        obj.output_dataset_collections.append(job_to_implicit_output_dataset_collection_association)
        obj.post_job_actions.append(post_job_action_association)
        obj.input_library_datasets.append(job_to_input_library_dataset_association)
        obj.output_library_datasets.append(job_to_output_library_dataset_association)
        obj.external_output_metadata.append(job_external_output_metadata)
        obj.tasks.append(task)
        obj.output_datasets.append(job_to_output_dataset_association)
        obj.state_history.append(job_state_history)
        obj.text_metrics.append(job_metric_text)
        obj.numeric_metrics.append(job_metric_numeric)
        obj.interactivetool_entry_points.append(interactive_tool_entry_point)
        obj.implicit_collection_jobs_association = implicit_collection_jobs_job_association
        obj.container = job_container_association
        obj.data_manager_association = data_manager_job_association
        add_object_to_object_session(obj, history_dataset_collection_association)
        obj.history_dataset_collection_associations.append(history_dataset_collection_association)
        obj.workflow_invocation_step = workflow_invocation_step

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id, unique=True)
            assert stored_obj.history_id == history.id
            assert stored_obj.library_folder_id == library_folder.id
            assert stored_obj.session_id == galaxy_session.id
            assert stored_obj.user_id == user.id
            assert collection_consists_of_objects(stored_obj.parameters, job_parameter)
            assert collection_consists_of_objects(stored_obj.input_datasets, job_to_input_dataset_association)
            assert collection_consists_of_objects(
                stored_obj.input_dataset_collections,
                job_to_input_dataset_collection_association,
            )
            assert collection_consists_of_objects(
                stored_obj.input_dataset_collection_elements,
                job_to_input_dataset_collection_element_association,
            )
            assert collection_consists_of_objects(
                stored_obj.output_dataset_collection_instances,
                job_to_output_dataset_collection_association,
            )
            assert collection_consists_of_objects(
                stored_obj.output_dataset_collections,
                job_to_implicit_output_dataset_collection_association,
            )
            assert collection_consists_of_objects(stored_obj.post_job_actions, post_job_action_association)
            assert collection_consists_of_objects(
                stored_obj.input_library_datasets,
                job_to_input_library_dataset_association,
            )
            assert collection_consists_of_objects(
                stored_obj.output_library_datasets,
                job_to_output_library_dataset_association,
            )
            assert collection_consists_of_objects(stored_obj.external_output_metadata, job_external_output_metadata)
            assert collection_consists_of_objects(stored_obj.tasks, task)
            assert collection_consists_of_objects(stored_obj.output_datasets, job_to_output_dataset_association)
            assert job_state_history in stored_obj.state_history  # sufficient for test
            assert collection_consists_of_objects(stored_obj.text_metrics, job_metric_text)
            assert collection_consists_of_objects(stored_obj.numeric_metrics, job_metric_numeric)
            assert collection_consists_of_objects(stored_obj.interactivetool_entry_points, interactive_tool_entry_point)
            assert stored_obj.implicit_collection_jobs_association == implicit_collection_jobs_job_association
            assert stored_obj.container == job_container_association
            assert stored_obj.data_manager_association == data_manager_job_association
            assert collection_consists_of_objects(
                stored_obj.history_dataset_collection_associations,
                history_dataset_collection_association,
            )
            assert stored_obj.workflow_invocation_step == workflow_invocation_step


class TestJobContainerAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "job_container_association"

    def test_columns(self, session, cls_, job):
        container_type = "a"
        container_name = "b"
        container_info = "c"
        created_time = now()
        modified_time = created_time + timedelta(hours=1)

        obj = cls_(job=job)
        obj.container_type = container_type
        obj.container_name = container_name
        obj.container_info = container_info
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
        obj = cls_(job=job)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id


class TestJobExportHistoryArchive(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "job_export_history_archive"

    def test_columns(self, session, cls_, job, history, dataset):
        compressed, history_attrs_filename = True, "a"
        obj = cls_()
        obj.job = job
        obj.history = history
        obj.dataset = dataset
        obj.compressed = compressed
        obj.history_attrs_filename = history_attrs_filename

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.job_id == job.id
            assert stored_obj.history_id == history.id
            assert stored_obj.dataset_id == dataset.id
            assert stored_obj.compressed == compressed
            assert stored_obj.history_attrs_filename == history_attrs_filename

    def test_relationships(self, session, cls_, job, history, dataset):
        obj = cls_()
        obj.job = job
        obj.history = history
        obj.dataset = dataset

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id
            assert stored_obj.history.id == history.id
            assert stored_obj.dataset.id == dataset.id


class TestJobExternalOutputMetadata(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "job_external_output_metadata"

    def test_columns(
        self,
        session,
        cls_,
        job,
        history_dataset_association,
        library_dataset_dataset_association,
    ):
        is_valid = False
        filename_in = "a"
        filename_out = "b"
        filename_results_code = "c"
        filename_kwds = "d"
        filename_override_metadata = "e"
        job_runner_external_pid = "f"

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

        # Expunge from session: we're creating and storing a new object that will recieve
        # the same primary key. This will trigger a SAWarning, since this identity already
        # exists in SQLAlchemy's identity map.
        session.expunge(stored_obj)
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
        library_dataset_dataset_association,
    ):
        # First test passing an hda
        obj = cls_(job, history_dataset_association)
        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id
            assert stored_obj.dataset.id == history_dataset_association.id

        # Expunge: see comment in test_columns()
        session.expunge(stored_obj)
        # Now pass an ldda
        obj = cls_(job, library_dataset_dataset_association)
        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.dataset.id == library_dataset_dataset_association.id


class TestJobImportHistoryArchive(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "job_import_history_archive"

    def test_columns(self, session, cls_, job, history):
        archive_dir = "a"
        obj = cls_(job=job, history=history, archive_dir=archive_dir)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.job_id == job.id
            assert stored_obj.history_id == history.id
            assert stored_obj.archive_dir == archive_dir

    def test_relationships(self, session, cls_, job, history):
        obj = cls_(job=job, history=history)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.job.id == job.id
            assert stored_obj.history.id == history.id


class TestJobMetricNumeric(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "job_metric_numeric"

    def test_columns(self, session, cls_, job):
        plugin, metric_name, metric_value = "a", "b", 9
        obj = cls_(plugin, metric_name, metric_value)
        obj.job_id = job.id

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.job_id == job.id
            assert stored_obj.plugin == plugin
            assert stored_obj.metric_value == metric_value


class TestJobMetricText(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "job_metric_text"

    def test_columns(self, session, cls_, job):
        plugin, metric_name, metric_value = "a", "b", "c"
        obj = cls_(plugin, metric_name, metric_value)
        obj.job_id = job.id

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.job_id == job.id
            assert stored_obj.plugin == plugin
            assert stored_obj.metric_value == metric_value


class TestJobParameter(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "job_parameter"

    def test_columns(self, session, cls_, job):
        name, value = "a", "b"
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
        assert cls_.__tablename__ == "job_state_history"

    def test_columns(self, session, cls_, job):
        state, info = job.state, job.info
        create_time = now()
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


class TestJobToImplicitOutputDatasetCollectionAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "job_to_implicit_output_dataset_collection"

    def test_columns(self, session, cls_, dataset_collection, job):
        name = "a"
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


class TestJobToInputDatasetAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "job_to_input_dataset"

    def test_columns(self, session, cls_, history_dataset_association, job):
        name, dataset_version = "a", 9
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


class TestJobToInputDatasetCollectionAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "job_to_input_dataset_collection"

    def test_columns(self, session, cls_, history_dataset_collection_association, job):
        name = "a"
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
        assert cls_.__tablename__ == "job_to_input_dataset_collection_element"

    def test_columns(self, session, cls_, dataset_collection_element, job):
        name = "a"
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


class TestJobToInputLibraryDatasetAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "job_to_input_library_dataset"

    def test_columns(self, session, cls_, library_dataset_dataset_association, job):
        name = "a"
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
        assert cls_.__tablename__ == "job_to_output_dataset"

    def test_columns(self, session, cls_, history_dataset_association, job):
        name = "a"
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
        assert cls_.__tablename__ == "job_to_output_dataset_collection"

    def test_columns(self, session, cls_, history_dataset_collection_association, job):
        name = "a"
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


class TestJobToOutputLibraryDatasetAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "job_to_output_library_dataset"

    def test_columns(self, session, cls_, library_dataset_dataset_association, job):
        name = "a"
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
        assert cls_.__tablename__ == "library"

    def test_columns(self, session, cls_, library_folder):
        name, deleted, purged, description, synopsis = "a", True, True, "b", "c"
        create_time = now()
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
    ):
        obj = cls_(None, None, None, library_folder)
        obj.actions.append(library_permission)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.root_folder.id == library_folder.id
            assert collection_consists_of_objects(stored_obj.actions, library_permission)


class TestLibraryDataset(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "library_dataset"

    def test_columns(self, session, cls_, library_folder):
        order_id = 9
        create_time = now()
        update_time = create_time + timedelta(hours=1)
        name = "a"
        info = "b"
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
        library_dataset_dataset_association_factory,
    ):
        obj = cls_()
        obj.folder = library_folder
        obj.library_dataset_dataset_association = library_dataset_dataset_association
        obj.actions.append(library_dataset_permission)

        ldda = library_dataset_dataset_association_factory()
        ldda.library_dataset = obj
        obj.actions.append(library_dataset_permission)
        persist(session, ldda)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.library_dataset_dataset_association.id == library_dataset_dataset_association.id
            assert stored_obj.folder.id == library_folder.id
            assert stored_obj.expired_datasets[0].id == ldda.id
            assert collection_consists_of_objects(stored_obj.actions, library_dataset_permission)

        delete_from_database(session, ldda)


class TestLibraryDatasetCollectionAnnotationAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "library_dataset_collection_annotation_association"

    def test_columns(self, session, cls_, library_dataset_collection_association, user):
        annotation = "a"
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


class TestLibraryDatasetCollectionAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "library_dataset_collection_association"

    def test_columns(self, session, cls_, dataset_collection, library_folder):
        name, deleted = "a", True
        obj = cls_()
        obj.collection = dataset_collection
        obj.folder = library_folder
        obj.name = name
        obj.deleted = deleted

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.collection_id == dataset_collection.id
            assert stored_obj.folder_id == library_folder.id
            assert stored_obj.name == name
            assert stored_obj.deleted == deleted

    def test_relationships(
        self,
        session,
        cls_,
        dataset_collection,
        library_folder,
        library_dataset_collection_annotation_association,
        library_dataset_collection_rating_association,
        library_dataset_collection_tag_association,
    ):

        obj = cls_()
        obj.collection = dataset_collection
        obj.folder = library_folder
        obj.tags.append(library_dataset_collection_tag_association)
        obj.annotations.append(library_dataset_collection_annotation_association)
        obj.ratings.append(library_dataset_collection_rating_association)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.collection.id == dataset_collection.id
            assert stored_obj.folder.id == library_folder.id
            assert collection_consists_of_objects(stored_obj.tags, library_dataset_collection_tag_association)
            assert collection_consists_of_objects(
                stored_obj.annotations,
                library_dataset_collection_annotation_association,
            )
            assert collection_consists_of_objects(stored_obj.ratings, library_dataset_collection_rating_association)


class TestLibraryDatasetCollectionRatingAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "library_dataset_collection_rating_association"

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


class TestLibraryDatasetCollectionTagAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "library_dataset_collection_tag_association"

    def test_columns(self, session, cls_, library_dataset_collection_association, tag, user):
        user_tname, value, user_value = "a", "b", "c"
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


class TestLibraryDatasetDatasetAssociation(BaseTest):
    def test_table(self, cls_):
        # mapped imperatively, so do not test cls_.__tablename__
        assert cls_.table.name == "library_dataset_dataset_association"

    def test_columns(
        self,
        session,
        cls_,
        library_dataset,
        dataset,
        history_dataset_association,
        library_dataset_dataset_association_factory,
        extended_metadata,
        user,
    ):
        create_time = now()
        state = "a"
        name = "b"
        info = "c"
        blurb = "d"
        peek = "e"
        tool_version = "f"
        extension = "g"
        designation = "i"
        deleted = True
        validated_state = "j"
        validated_state_message = "k"
        visible = True
        message = "m"
        _metadata = {"key": "value"}
        copied_from_ldda = library_dataset_dataset_association_factory()
        parent = library_dataset_dataset_association_factory()
        persist(session, copied_from_ldda)
        persist(session, parent)

        obj = cls_()
        obj.library_dataset = library_dataset
        add_object_to_object_session(obj, dataset)
        obj.dataset = dataset
        obj.create_time = create_time
        obj.copied_from_history_dataset_association = history_dataset_association
        obj.copied_from_library_dataset_dataset_association = copied_from_ldda
        obj.state = state
        obj.name = name
        obj.info = info
        obj.blurb = blurb
        obj.peek = peek
        obj.tool_version = tool_version
        obj.extension = extension
        obj.parent_id = parent.id
        obj.designation = designation
        obj.deleted = deleted
        obj.validated_state = validated_state
        obj.validated_state_message = validated_state_message
        obj.visible = visible
        obj.extended_metadata = extended_metadata
        obj.user = user
        obj.message = message
        obj._metadata = _metadata

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.library_dataset_id == library_dataset.id
            assert stored_obj.dataset_id == dataset.id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time >= create_time  # this is sufficient for testing
            assert stored_obj.copied_from_history_dataset_association_id == history_dataset_association.id
            assert stored_obj.copied_from_library_dataset_dataset_association_id == copied_from_ldda.id
            assert stored_obj.state == state
            assert stored_obj.name == name
            assert stored_obj.info == info
            assert stored_obj.blurb == blurb
            assert stored_obj.peek == peek
            assert stored_obj.tool_version == tool_version
            assert stored_obj.extension == extension
            assert stored_obj.parent_id == parent.id
            assert stored_obj.designation == designation
            assert stored_obj.deleted == deleted
            assert stored_obj.validated_state == validated_state
            assert stored_obj.validated_state_message == validated_state_message
            assert stored_obj.visible == visible
            assert stored_obj.extended_metadata_id == extended_metadata.id
            assert stored_obj.user_id == user.id
            assert stored_obj.message == message
            # We cannot test obj.metadata by setting it directly (like the other attributes).
            # However, the following assertion verifies that it exists and has been initialized correctly.
            assert stored_obj.metadata.parent.id == obj_id
            assert stored_obj._metadata == _metadata

        delete_from_database(session, [copied_from_ldda, parent])

    def test_relationships(
        self,
        session,
        cls_,
        library_dataset,
        dataset,
        history_dataset_association,
        library_dataset_dataset_association_factory,
        extended_metadata,
        user,
        library_dataset_dataset_association_tag_association,
        library_dataset_dataset_association_permission,
        history_dataset_association_factory,
        implicitly_converted_dataset_association_factory,
        job_to_input_library_dataset_association,
        job_to_output_library_dataset_association,
    ):
        copied_from_ldda = library_dataset_dataset_association_factory()
        copied_to_ldda = library_dataset_dataset_association_factory()
        parent = library_dataset_dataset_association_factory()
        copied_to_hda = history_dataset_association_factory()
        icda = implicitly_converted_dataset_association_factory()
        icpda = implicitly_converted_dataset_association_factory()
        persisted = [
            copied_from_ldda,
            copied_to_ldda,
            parent,
            copied_to_hda,
            icda,
            icpda,
        ]

        obj = cls_()
        obj.library_dataset = library_dataset
        add_object_to_object_session(obj, dataset)
        obj.dataset = dataset
        obj.copied_from_history_dataset_association = history_dataset_association
        obj.copied_from_library_dataset_dataset_association = copied_from_ldda
        obj.extended_metadata = extended_metadata
        obj.user = user
        obj.tags.append(library_dataset_dataset_association_tag_association)
        obj.actions.append(library_dataset_dataset_association_permission)
        obj.copied_to_history_dataset_associations.append(copied_to_hda)
        obj.copied_to_library_dataset_dataset_associations.append(copied_to_ldda)
        obj.implicitly_converted_datasets.append(icda)
        obj.implicitly_converted_parent_datasets.append(icpda)
        obj.dependent_jobs.append(job_to_input_library_dataset_association)
        obj.creating_job_associations.append(job_to_output_library_dataset_association)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.library_dataset.id == library_dataset.id
            assert stored_obj.dataset.id == dataset.id
            assert stored_obj.copied_from_history_dataset_association.id == history_dataset_association.id
            assert stored_obj.copied_from_library_dataset_dataset_association.id == copied_from_ldda.id
            assert stored_obj.extended_metadata.id == extended_metadata.id
            assert stored_obj.user.id == user.id
            assert collection_consists_of_objects(stored_obj.tags, library_dataset_dataset_association_tag_association)
            assert collection_consists_of_objects(stored_obj.actions, library_dataset_dataset_association_permission)
            assert collection_consists_of_objects(stored_obj.copied_to_history_dataset_associations, copied_to_hda)
            assert collection_consists_of_objects(
                stored_obj.copied_to_library_dataset_dataset_associations,
                copied_to_ldda,
            )
            assert collection_consists_of_objects(stored_obj.implicitly_converted_datasets, icda)
            assert collection_consists_of_objects(stored_obj.implicitly_converted_parent_datasets, icpda)
            assert collection_consists_of_objects(stored_obj.dependent_jobs, job_to_input_library_dataset_association)
            assert collection_consists_of_objects(
                stored_obj.creating_job_associations,
                job_to_output_library_dataset_association,
            )

        delete_from_database(session, persisted)


class TestLibraryDatasetDatasetAssociationPermissions(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "library_dataset_dataset_association_permissions"

    def test_columns(self, session, cls_, library_dataset_dataset_association, role):
        action = "a"
        create_time = now()
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
        assert cls_.__tablename__ == "library_dataset_dataset_association_tag_association"

    def test_columns(self, session, cls_, library_dataset_dataset_association, tag, user):
        user_tname, value, user_value = "a", "b", "c"
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


class TestLibraryDatasetDatasetInfoAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "library_dataset_dataset_info_association"

    def test_columns(
        self,
        session,
        cls_,
        library_dataset_dataset_association,
        form_definition,
        form_values,
    ):
        deleted = True
        obj = cls_(library_dataset_dataset_association, form_definition, form_values)
        obj.deleted = deleted

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.library_dataset_dataset_association_id == library_dataset_dataset_association.id
            assert stored_obj.form_definition_id == form_definition.id
            assert stored_obj.form_values_id == form_values.id
            assert stored_obj.deleted == deleted

    def test_relationships(
        self,
        session,
        cls_,
        library_dataset_dataset_association,
        form_definition,
        form_values,
    ):
        obj = cls_(library_dataset_dataset_association, form_definition, form_values)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.library_dataset_dataset_association.id == library_dataset_dataset_association.id
            assert stored_obj.template.id == form_definition.id
            assert stored_obj.info.id == form_values.id


class TestLibraryDatasetPermissions(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "library_dataset_permissions"

    def test_columns(self, session, cls_, library_dataset, role):
        action = "a"
        create_time = now()
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
        assert cls_.__tablename__ == "library_folder"
        assert has_index(cls_.__table__, ("name",))

    def test_columns(self, session, cls_, library_folder):
        parent = library_folder
        create_time = now()
        update_time = create_time + timedelta(hours=1)
        name = "a"
        description = "b"
        order_id = 9
        item_count = 1
        deleted = False
        purged = False
        genome_build = "c"

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
        self,
        session,
        cls_,
        library_folder,
        library_dataset,
        library,
        library_folder_permission,
        library_folder_factory,
    ):
        obj = cls_()
        add_object_to_object_session(obj, library_folder)
        obj.parent = library_folder
        folder1 = library_folder_factory()
        obj.folders.append(folder1)
        obj.library_root.append(library)
        obj.actions.append(library_folder_permission)

        # There's no back reference, so dataset does not update folder; so we have to flush to the database
        library_dataset.folder = obj
        persist(session, library_dataset)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.parent.id == library_folder.id
            assert collection_consists_of_objects(stored_obj.folders, folder1)
            assert collection_consists_of_objects(stored_obj.active_folders, folder1)
            assert collection_consists_of_objects(stored_obj.library_root, library)
            assert collection_consists_of_objects(stored_obj.actions, library_folder_permission)
            # use identity equality instread of object equality.
            assert stored_obj.datasets[0].id == library_dataset.id
            assert stored_obj.active_datasets[0].id == library_dataset.id

        delete_from_database(session, folder1)


class TestLibraryFolderInfoAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "library_folder_info_association"

    def test_columns(self, session, cls_, library_folder, form_definition, form_values):
        inheritable, deleted = True, True
        obj = cls_(library_folder, form_definition, form_values, inheritable)
        obj.deleted = deleted

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.library_folder_id == library_folder.id
            assert stored_obj.form_definition_id == form_definition.id
            assert stored_obj.form_values_id == form_values.id
            assert stored_obj.inheritable == inheritable
            assert stored_obj.deleted == deleted

    def test_relationships(self, session, cls_, library_folder, form_definition, form_values):
        obj = cls_(library_folder, form_definition, form_values)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.folder.id == library_folder.id
            assert stored_obj.template.id == form_definition.id
            assert stored_obj.info.id == form_values.id


class TestLibraryFolderPermissions(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "library_folder_permissions"

    def test_columns(self, session, cls_, library_folder, role):
        action = "a"
        obj = cls_(action, library_folder, role)
        create_time = now()
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
        assert cls_.__tablename__ == "library_info_association"

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
        assert cls_.__tablename__ == "library_permissions"

    def test_columns(self, session, cls_, library, role):
        action = "a"
        obj = cls_(action, library, role)
        create_time = now()
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


class TestMetadataFile(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "metadata_file"

    def test_columns(
        self,
        session,
        cls_,
        history_dataset_association,
        library_dataset_dataset_association,
    ):
        name = "a"
        create_time = now()
        update_time = create_time + timedelta(hours=1)
        object_store_id = "b"
        uuid = uuid4()
        deleted = True
        purged = True

        obj = cls_()
        obj.name = name
        obj.history_dataset = history_dataset_association
        obj.library_dataset = library_dataset_dataset_association
        obj.create_time = create_time
        obj.update_time = update_time
        obj.object_store_id = object_store_id
        obj.uuid = uuid
        obj.deleted = deleted
        obj.purged = purged

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.name == name
            assert stored_obj.hda_id == history_dataset_association.id
            assert stored_obj.lda_id == library_dataset_dataset_association.id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.object_store_id == object_store_id
            assert stored_obj.uuid == uuid
            assert stored_obj.deleted == deleted
            assert stored_obj.purged == purged

    def test_relationships(
        self,
        session,
        cls_,
        history_dataset_association,
        library_dataset_dataset_association,
    ):
        obj = cls_()
        obj.history_dataset = history_dataset_association
        obj.library_dataset = library_dataset_dataset_association

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.history_dataset.id == history_dataset_association.id
            assert stored_obj.library_dataset.id == library_dataset_dataset_association.id


class TestPSAAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "psa_association"

    def test_columns(self, session, cls_):
        server_url, handle, secret, issued, lifetime, assoc_type = (
            "a",
            "b",
            "c",
            1,
            2,
            "d",
        )
        obj = cls_()
        obj.server_url = server_url
        obj.handle = handle
        obj.secret = secret
        obj.issued = issued
        obj.lifetime = lifetime
        obj.assoc_type = assoc_type

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
        assert cls_.__tablename__ == "psa_code"
        assert has_unique_constraint(cls_.__table__, ("code", "email"))

    def test_columns(self, session, cls_):
        email, code = "a", get_unique_value()
        obj = cls_(email, code)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.email == email
            assert stored_obj.code == code


class TestPSANonce(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "psa_nonce"

    def test_columns(self, session, cls_):
        server_url, timestamp, salt = "a", 1, "b"
        obj = cls_(server_url, timestamp, salt)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.server_url
            assert stored_obj.timestamp == timestamp
            assert stored_obj.salt == salt


class TestPSAPartial(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "psa_partial"

    def test_columns(self, session, cls_):
        token, data, next_step, backend = "a", "b", 1, "c"
        obj = cls_(token, data, next_step, backend)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.token == token
            assert stored_obj.data == data
            assert stored_obj.next_step == next_step
            assert stored_obj.backend == backend


class TestPage(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "page"
        assert has_index(cls_.__table__, ("slug",))

    def test_columns(self, session, cls_, user, page_revision):
        title, deleted, importable, slug, published = "a", True, True, "b", True
        create_time = now()
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
            assert collection_consists_of_objects(stored_obj.revisions, page_revision)
            assert stored_obj.latest_revision.id == page_revision.id
            assert collection_consists_of_objects(stored_obj.tags, page_tag_association)
            assert collection_consists_of_objects(stored_obj.annotations, page_annotation_association)
            assert collection_consists_of_objects(stored_obj.ratings, page_rating_association)
            assert collection_consists_of_objects(stored_obj.users_shared_with, page_user_share_association)
            # This doesn't test the average amount, just the mapping.
            assert stored_obj.average_rating == page_rating_association.rating

    def test_average_rating(self, session, page, user, page_rating_association_factory):
        _run_average_rating_test(session, page, user, page_rating_association_factory)


class TestPageAnnotationAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "page_annotation_association"
        assert has_index(cls_.__table__, ("annotation",))

    def test_columns(self, session, cls_, page, user):
        annotation = "a"
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
        assert cls_.__tablename__ == "page_rating_association"

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
        assert cls_.__tablename__ == "page_revision"

    def test_columns(self, session, cls_, page):
        title, content = "a", "b"
        create_time = now()
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
        assert cls_.__tablename__ == "page_tag_association"

    def test_columns(self, session, cls_, page, tag, user):
        user_tname, value, user_value = "a", "b", "c"
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
        assert cls_.__tablename__ == "page_user_share_association"

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
        assert cls_.__tablename__ == "password_reset_token"

    def test_columns_and_relationships(self, session, cls_, user):
        token = get_unique_value()
        expiration_time = now()
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
        assert cls_.__tablename__ == "post_job_action"

    def test_columns(self, session, cls_, workflow_step):
        action_type = "a"
        output_name = "b"
        action_arguments = "c"
        obj = cls_(action_type, workflow_step, output_name, action_arguments)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.workflow_step_id == workflow_step.id
            assert stored_obj.action_type == action_type
            assert stored_obj.output_name == output_name
            assert stored_obj.action_arguments == action_arguments

    def test_relationships(self, session, cls_, workflow_step):
        obj = cls_("a", workflow_step, None, None)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.workflow_step.id == workflow_step.id


class TestPostJobActionAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "post_job_action_association"

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


class TestQuota(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "quota"

    def test_columns(self, session, cls_):
        name, description, amount, operation = get_unique_value(), "b", 42, "+"
        create_time = now()
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

    def test_relationships(
        self,
        session,
        cls_,
        default_quota_association,
        group_quota_association,
        user_quota_association,
    ):
        def add_association(assoc_object, assoc_attribute):
            assoc_object.quota = obj
            getattr(obj, assoc_attribute).append(assoc_object)

        obj = cls_(get_unique_value(), None, 1, "+")
        add_association(default_quota_association, "default")
        add_association(group_quota_association, "groups")
        add_association(user_quota_association, "users")

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert collection_consists_of_objects(stored_obj.default, default_quota_association)
            assert collection_consists_of_objects(stored_obj.groups, group_quota_association)
            assert collection_consists_of_objects(stored_obj.users, user_quota_association)


class TestRole(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "role"

    def test_columns(self, session, cls_):
        name, description, type_, deleted = (
            get_unique_value(),
            "b",
            cls_.types.SYSTEM,
            True,
        )
        create_time = now()
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
        user_role_association,
    ):
        name, description, type_ = get_unique_value(), "b", cls_.types.SYSTEM
        obj = cls_(name, description, type_)
        obj.dataset_actions.append(dataset_permission)
        obj.groups.append(group_role_association)
        obj.users.append(user_role_association)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert collection_consists_of_objects(stored_obj.dataset_actions, dataset_permission)
            assert collection_consists_of_objects(stored_obj.groups, group_role_association)
            assert collection_consists_of_objects(stored_obj.users, user_role_association)


class TestStoredWorkflow(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "stored_workflow"
        assert has_index(cls_.__table__, ("slug",))

    def test_columns(self, session, cls_, workflow, user):
        create_time = now()
        update_time = create_time + timedelta(hours=1)
        name = "a"
        deleted = True
        hidden = True
        importable = True
        slug = "b"
        from_path = "c"
        published = True

        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.user = user
        obj.latest_workflow = workflow
        obj.name = name
        obj.deleted = deleted
        obj.hidden = hidden
        obj.importable = importable
        obj.slug = slug
        obj.from_path = from_path
        obj.published = published

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id, unique=True)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.user_id == user.id
            assert stored_obj.latest_workflow_id == workflow.id
            assert stored_obj.name == name
            assert stored_obj.deleted == deleted
            assert stored_obj.hidden == hidden
            assert stored_obj.importable == importable
            assert stored_obj.slug == slug
            assert stored_obj.from_path == from_path
            assert stored_obj.published == published

    def test_relationships(
        self,
        session,
        cls_,
        workflow,
        user,
        workflow_factory,
        stored_workflow_tag_association,
        stored_workflow_annotation_association,
        stored_workflow_rating_association,
        stored_workflow_tag_association_factory,
        stored_workflow_user_share_association,
    ):
        obj = cls_()
        obj.user = user
        obj.latest_workflow = workflow
        obj.tags.append(stored_workflow_tag_association)
        obj.annotations.append(stored_workflow_annotation_association)
        obj.ratings.append(stored_workflow_rating_association)
        obj.users_shared_with.append(stored_workflow_user_share_association)

        # setup workflow for testing workflows attribure
        wf = workflow_factory()
        wf.stored_workflow = obj

        # setup owner tag association for testing owner_tags
        tag_assoc2 = stored_workflow_tag_association_factory()
        tag_assoc2.user = user
        tag_assoc2.stored_workflow = obj

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id, unique=True)
            assert stored_obj.user.id == user.id
            assert stored_obj.latest_workflow.id == workflow.id
            assert stored_obj.workflows[0].id == wf.id
            assert collection_consists_of_objects(stored_obj.annotations, stored_workflow_annotation_association)
            assert collection_consists_of_objects(stored_obj.ratings, stored_workflow_rating_association)
            # This doesn't test the average amount, just the mapping.
            assert stored_obj.average_rating == stored_workflow_rating_association.rating
            assert collection_consists_of_objects(stored_obj.tags, stored_workflow_tag_association, tag_assoc2)
            assert collection_consists_of_objects(stored_obj.owner_tags, tag_assoc2)
            assert collection_consists_of_objects(stored_obj.users_shared_with, stored_workflow_user_share_association)

        delete_from_database(session, [wf, tag_assoc2])

    def test_average_rating(self, session, stored_workflow, user, stored_workflow_rating_association_factory):
        _run_average_rating_test(session, stored_workflow, user, stored_workflow_rating_association_factory)


class TestStoredWorkflowAnnotationAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "stored_workflow_annotation_association"
        assert has_index(cls_.__table__, ("annotation",))

    def test_columns(self, session, cls_, stored_workflow, user):
        annotation = "a"
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


class TestStoredWorkflowMenuEntry(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "stored_workflow_menu_entry"

    def test_columns(self, session, cls_, stored_workflow, user):
        order_index = 1
        obj = cls_()
        obj.stored_workflow = stored_workflow
        add_object_to_object_session(obj, user)
        obj.user = user
        obj.order_index = order_index

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.stored_workflow_id == stored_workflow.id
            assert stored_obj.user_id == user.id
            assert stored_obj.order_index == order_index

    def test_relationships(self, session, cls_, stored_workflow, user):
        obj = cls_()
        obj.stored_workflow = stored_workflow
        add_object_to_object_session(obj, user)
        obj.user = user

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.stored_workflow.id == stored_workflow.id
            assert stored_obj.user.id == user.id


class TestStoredWorkflowRatingAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "stored_workflow_rating_association"

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
        assert cls_.__tablename__ == "stored_workflow_tag_association"

    def test_columns(self, session, cls_, stored_workflow, tag, user):
        user_tname, value, user_value = "a", "b", "c"
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


class TestStoredWorkflowUserShareAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "stored_workflow_user_share_connection"

    def test_columns(self, session, cls_, stored_workflow, user):
        obj = cls_()
        obj.stored_workflow = stored_workflow
        obj.user = user

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.stored_workflow_id == stored_workflow.id
            assert stored_obj.user_id == user.id

    def test_relationships(self, session, cls_, stored_workflow, user):
        obj = cls_()
        obj.stored_workflow = stored_workflow
        obj.user = user

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.stored_workflow.id == stored_workflow.id
            assert stored_obj.user.id == user.id


class TestTag(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "tag"
        assert has_unique_constraint(cls_.__table__, ("name",))

    def test_columns(self, session, cls_):
        parent_tag = cls_()
        type_, name = 1, "a"
        obj = cls_(type=type_, name=name)
        obj.parent = parent_tag

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.type == type_
            assert stored_obj.parent_id == parent_tag.id
            assert stored_obj.name == name

        delete_from_database(session, parent_tag)

    def test_relationships(
        self,
        session,
        cls_,
    ):
        obj = cls_()
        parent_tag = cls_()
        child_tag = cls_()
        obj.parent = parent_tag
        obj.children.append(child_tag)

        def add_association(assoc_object, assoc_attribute):
            assoc_object.tag = obj
            getattr(obj, assoc_attribute).append(assoc_object)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.parent.id == parent_tag.id
            assert collection_consists_of_objects(stored_obj.children, child_tag)

        delete_from_database(session, [parent_tag, child_tag])


class TestTask(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "task"

    def test_columns(self, session, cls_, job):
        create_time = now()
        execution_time = create_time + timedelta(hours=1)
        update_time = execution_time + timedelta(hours=1)
        state = "p"
        command_line = "a"
        param_filename = "b"
        runner_name = "c"
        job_stdout = "d"
        job_stderr = "e"
        tool_stdout = "f"
        tool_stderr = "g"
        exit_code = 9
        job_messages = "h"
        info = "i"
        traceback = "j"
        working_directory = "k"
        task_runner_name = "l"
        task_runner_external_id = "m"
        prepare_input_files_cmd = "n"

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
            assert collection_consists_of_objects(stored_obj.numeric_metrics, task_metric_numeric)
            assert collection_consists_of_objects(stored_obj.text_metrics, task_metric_text)


class TestTaskMetricNumeric(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "task_metric_numeric"

    def test_columns(self, session, cls_, task):
        plugin, metric_name, metric_value = "a", "b", 9
        obj = cls_(plugin, metric_name, metric_value)
        obj.task_id = task.id

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.task_id == task.id
            assert stored_obj.plugin == plugin
            assert stored_obj.metric_value == metric_value


class TestTaskMetricText(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "task_metric_text"

    def test_columns(self, session, cls_, task):
        plugin, metric_name, metric_value = "a", "b", "c"
        obj = cls_(plugin, metric_name, metric_value)
        obj.task_id = task.id

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.task_id == task.id
            assert stored_obj.plugin == plugin
            assert stored_obj.metric_value == metric_value


class TestToolTagAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "tool_tag_association"

    def test_columns(self, session, cls_, tag, user):
        user_tname, value, user_value, tool_id = "a", "b", "c", "d"
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


class TestUser(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "galaxy_user"

    def test_columns(self, session, cls_, form_values):
        create_time = now()
        update_time = create_time + timedelta(hours=1)
        email = get_unique_value()
        username = get_unique_value()
        password = "c"
        last_password_change = update_time
        external = True
        deleted = True
        purged = True
        disk_usage = 1
        active = False
        activation_token = "d"

        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.email = email
        obj.username = username
        obj.password = password
        obj.last_password_change = last_password_change
        obj.external = external
        obj.values = form_values
        obj.deleted = deleted
        obj.purged = purged
        obj.disk_usage = disk_usage
        obj.active = active
        obj.activation_token = activation_token

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.email == email
            assert stored_obj.username == username
            assert stored_obj.password == password
            assert stored_obj.last_password_change == last_password_change
            assert stored_obj.external == external
            assert stored_obj.form_values_id == form_values.id
            assert stored_obj.deleted == deleted
            assert stored_obj.purged == purged
            assert stored_obj.disk_usage == disk_usage
            assert stored_obj.active == active
            assert stored_obj.activation_token == activation_token

    def test_relationships(
        self,
        session,
        cls_,
        form_values,
        user_address,
        cloud_authz,
        custos_authnz_token,
        default_user_permissions,
        user_group_association,
        history_factory,
        galaxy_session,
        user_quota_association,
        user_authnz_token,
        user_preference,
        api_keys,
        data_manager_history_association,
        role_factory,
        user_role_association_factory,
        stored_workflow,
        stored_workflow_menu_entry_factory,
    ):
        cleanup = []

        history1 = history_factory(deleted=False)
        cleanup.append(history1)
        history2 = history_factory(deleted=True)
        cleanup.append(history2)

        obj = cls_()

        obj.email = get_unique_value()
        obj.username = get_unique_value()
        obj.password = "a"
        obj.values = form_values
        obj.addresses.append(user_address)
        obj.cloudauthz.append(cloud_authz)
        obj.custos_auth.append(custos_authnz_token)
        obj.default_permissions.append(default_user_permissions)
        obj.groups.append(user_group_association)
        obj.histories.append(history1)
        obj.histories.append(history2)
        obj.galaxy_sessions.append(galaxy_session)
        obj.quotas.append(user_quota_association)
        obj.social_auth.append(user_authnz_token)

        _private_role = role_factory(name=obj.email)
        cleanup.append(_private_role)

        private_user_role = user_role_association_factory(obj, _private_role)
        cleanup.append(private_user_role)

        obj.roles.append(private_user_role)

        _non_private_role = role_factory(name="a")
        cleanup.append(_non_private_role)

        non_private_user_role = user_role_association_factory(obj, _non_private_role)
        cleanup.append(non_private_user_role)

        obj.roles.append(non_private_user_role)

        swme = stored_workflow_menu_entry_factory()
        cleanup.append(swme)

        swme.stored_workflow = stored_workflow
        swme.user = obj

        user_preference.name = "a"
        obj._preferences.set(user_preference)

        obj.api_keys.append(api_keys)
        obj.data_manager_histories.append(data_manager_history_association)
        obj.stored_workflows.append(stored_workflow)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.values.id == form_values.id
            assert collection_consists_of_objects(stored_obj.addresses, user_address)
            assert collection_consists_of_objects(stored_obj.cloudauthz, cloud_authz)
            assert collection_consists_of_objects(stored_obj.custos_auth, custos_authnz_token)
            assert collection_consists_of_objects(stored_obj.default_permissions, default_user_permissions)
            assert collection_consists_of_objects(stored_obj.groups, user_group_association)
            assert collection_consists_of_objects(stored_obj.histories, history1, history2)
            assert collection_consists_of_objects(stored_obj.active_histories, history1)
            assert collection_consists_of_objects(stored_obj.galaxy_sessions, galaxy_session)
            assert collection_consists_of_objects(stored_obj.quotas, user_quota_association)
            assert collection_consists_of_objects(stored_obj.social_auth, user_authnz_token)
            assert collection_consists_of_objects(stored_obj.stored_workflow_menu_entries, swme)
            assert user_preference in stored_obj._preferences.values()
            assert collection_consists_of_objects(stored_obj.api_keys, api_keys)
            assert collection_consists_of_objects(stored_obj.data_manager_histories, data_manager_history_association)
            assert collection_consists_of_objects(stored_obj.roles, private_user_role, non_private_user_role)
            assert collection_consists_of_objects(stored_obj.non_private_roles, non_private_user_role)
            assert collection_consists_of_objects(stored_obj.stored_workflows, stored_workflow)

        delete_from_database(session, cleanup)


class TestUserAction(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "user_action"

    def test_columns(self, session, cls_, user, galaxy_session):
        action, params, context = "a", "b", "c"
        create_time = now()
        obj = cls_()
        obj.user = user
        obj.session_id = galaxy_session.id
        obj.action = action
        obj.params = params
        obj.context = context
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

    def test_relationships(self, session, cls_, user):
        obj = cls_()
        obj.user = user

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.user.id == user.id


class TestUserAddress(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "user_address"

    def test_columns_and_relationships(self, session, cls_, user):
        (
            desc,
            name,
            institution,
            address,
            city,
            state,
            postal_code,
            country,
            phone,
            deleted,
            purged,
        ) = ("a", "b", "c", "d", "e", "f", "g", "h", "i", True, False)
        create_time = now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_()
        obj.user = user
        obj.desc = desc
        obj.name = name
        obj.institution = institution
        obj.address = address
        obj.city = city
        obj.state = state
        obj.postal_code = postal_code
        obj.country = country
        obj.phone = phone
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
        assert cls_.__tablename__ == "oidc_user_authnz_tokens"
        assert has_unique_constraint(cls_.__table__, ("provider", "uid"))

    def test_columns(self, session, cls_, user):
        provider, uid, extra_data, lifetime, assoc_type = (
            get_unique_value(),
            "b",
            "c",
            1,
            "d",
        )
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

    def test_relationships(self, session, cls_, user):
        obj = cls_(get_unique_value(), None, user=user)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.user.id == user.id


class TestUserGroupAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "user_group_association"

    def test_columns(self, session, cls_, user, group):
        create_time = now()
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


class TestUserPreference(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "user_preference"

    def test_columns(self, session, cls_, user):
        name, value = "a", "b"
        obj = cls_()
        obj.name = name
        obj.value = value
        obj.user_id = user.id

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.name == name
            assert stored_obj.value == value
            assert stored_obj.user_id == user.id


class TestUserQuotaAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "user_quota_association"

    def test_columns(self, session, cls_, user, quota):
        create_time = now()
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


class TestUserRoleAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "user_role_association"

    def test_columns(self, session, cls_, user, role):
        create_time = now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_(user, role)
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.user_id == user.id
            assert stored_obj.role_id == role.id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time

    def test_relationships(self, session, cls_, user, role):
        obj = cls_(user, role)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.user.id == user.id
            assert stored_obj.role.id == role.id


class TestVault(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "vault"

    def test_columns(self, session, cls_):
        create_time = update_time = now()
        key = "/some/path"
        parent_key = "/some"
        value = "helloworld"
        obj = cls_(create_time=create_time, update_time=update_time, key=key, parent_key=parent_key, value=value)

        with dbcleanup(session, obj, where_clause=cls_.key == key):
            stored_obj = get_stored_obj(session, cls_, where_clause=cls_.key == key)
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.key == key
            assert stored_obj.parent_key == parent_key
            assert stored_obj.value == value


class TestVisualization(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "visualization"
        assert has_index(cls_.__table__, ("dbkey",))
        assert has_index(cls_.__table__, ("slug",))

    def test_columns(self, session, cls_, user, visualization_revision):
        create_time = now()
        update_time = create_time + timedelta(hours=1)
        title = "a"
        type = "b"
        dbkey = "c"
        deleted = True
        importable = True
        slug = "d"
        published = True

        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.user = user
        obj.latest_revision = visualization_revision
        obj.title = title
        obj.type = type
        obj.dbkey = dbkey
        obj.deleted = deleted
        obj.importable = importable
        obj.slug = slug
        obj.published = published

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.user_id == user.id
            assert stored_obj.latest_revision_id == visualization_revision.id
            assert stored_obj.title == title
            assert stored_obj.type == type
            assert stored_obj.dbkey == dbkey
            assert stored_obj.deleted == deleted
            assert stored_obj.importable == importable
            assert stored_obj.slug == slug
            assert stored_obj.published == published

    def test_relationships(
        self,
        session,
        cls_,
        user,
        visualization_revision,
        visualization_tag_association,
        visualization_annotation_association,
        visualization_rating_association,
        visualization_revision_factory,
        visualization_user_share_association,
    ):
        revision2 = visualization_revision_factory()
        persist(session, revision2)

        obj = cls_()
        obj.user = user
        obj.latest_revision = visualization_revision
        obj.revisions.append(revision2)
        obj.tags.append(visualization_tag_association)
        obj.annotations.append(visualization_annotation_association)
        obj.ratings.append(visualization_rating_association)
        obj.users_shared_with.append(visualization_user_share_association)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.user.id == user.id
            assert stored_obj.latest_revision.id == visualization_revision.id
            assert collection_consists_of_objects(stored_obj.revisions, revision2)
            assert collection_consists_of_objects(stored_obj.tags, visualization_tag_association)
            assert collection_consists_of_objects(stored_obj.annotations, visualization_annotation_association)
            assert collection_consists_of_objects(stored_obj.ratings, visualization_rating_association)
            # This doesn't test the average amount, just the mapping.
            assert stored_obj.average_rating == visualization_rating_association.rating
            assert collection_consists_of_objects(stored_obj.users_shared_with, visualization_user_share_association)

        delete_from_database(session, revision2)

    def test_average_rating(self, session, visualization, user, visualization_rating_association_factory):
        _run_average_rating_test(session, visualization, user, visualization_rating_association_factory)


class TestVisualizationAnnotationAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "visualization_annotation_association"
        assert has_index(cls_.__table__, ("annotation",))

    def test_columns(self, session, cls_, visualization, user):
        annotation = "a"
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
        assert cls_.__tablename__ == "visualization_rating_association"

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
        assert cls_.__tablename__ == "visualization_revision"
        assert has_index(cls_.__table__, ("dbkey",))

    def test_columns(self, session, cls_, visualization):
        visualization, title, dbkey, config = visualization, "a", "b", "c"
        create_time = now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_()
        obj.visualization = visualization
        obj.title = title
        obj.dbkey = dbkey
        obj.config = config

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
        obj = cls_(visualization=visualization)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.visualization.id == visualization.id


class TestVisualizationTagAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "visualization_tag_association"

    def test_columns(self, session, cls_, visualization, tag, user):
        user_tname, value, user_value = "a", "b", "c"
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


class TestVisualizationUserShareAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "visualization_user_share_association"

    def test_columns(self, session, cls_, visualization, user):
        obj = cls_()
        obj.visualization = visualization
        obj.user = user

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.visualization_id == visualization.id
            assert stored_obj.user_id == user.id

    def test_relationships(self, session, cls_, visualization, user):
        obj = cls_()
        obj.visualization = visualization
        obj.user = user

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.visualization.id == visualization.id
            assert stored_obj.user.id == user.id


class TestWorkerProcess(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "worker_process"
        assert has_unique_constraint(cls_.__table__, ("server_name", "hostname"))

    def test_columns(self, session, cls_):
        server_name, hostname = get_unique_value(), "a"
        update_time = now()
        obj = cls_()
        obj.server_name = server_name
        obj.hostname = hostname
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.server_name == server_name
            assert stored_obj.hostname == hostname
            assert stored_obj.pid is None
            assert stored_obj.update_time == update_time


class TestWorkflow(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "workflow"

    def test_columns(self, session, cls_, stored_workflow, workflow):
        create_time = now()
        update_time = create_time + timedelta(hours=1)
        name = "a"
        has_cycles = True
        has_errors = True
        reports_config = "b"
        creator_metadata = "c"
        license = "d"
        source_metadata = "e"
        uuid = uuid4()

        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.stored_workflow = stored_workflow
        obj.parent_workflow_id = workflow.id
        obj.name = name
        obj.has_cycles = has_cycles
        obj.has_errors = has_errors
        obj.reports_config = reports_config
        obj.creator_metadata = creator_metadata
        obj.license = license
        obj.source_metadata = source_metadata
        obj.uuid = uuid

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id, unique=True)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.stored_workflow_id == stored_workflow.id
            assert stored_obj.parent_workflow_id == workflow.id
            assert stored_obj.name == name
            assert stored_obj.has_cycles == has_cycles
            assert stored_obj.has_errors == has_errors
            assert stored_obj.reports_config == reports_config
            assert stored_obj.creator_metadata == creator_metadata
            assert stored_obj.license == license
            assert stored_obj.source_metadata == source_metadata
            assert stored_obj.uuid == uuid

    def test_relationships(self, session, cls_, stored_workflow, workflow, workflow_step_factory):
        obj = cls_()
        obj.stored_workflow = stored_workflow
        obj.parent_workflow_id = workflow.id

        # Setup workflow steps to test attribures: steps, parent_workflow_step
        workflow_step = workflow_step_factory(workflow=obj)
        parent_workflow_step = workflow_step_factory(subworkflow=obj)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id, unique=True)
            assert stored_obj.stored_workflow_id == stored_workflow.id
            assert stored_obj.parent_workflow_id == workflow.id
            assert stored_obj.steps[0].id == workflow_step.id
            assert stored_obj.step_count == 1
            assert stored_obj.parent_workflow_steps[0].id == parent_workflow_step.id

        delete_from_database(session, [workflow_step, parent_workflow_step])


class TestWorkflowInvocation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "workflow_invocation"

    def test_columns(self, session, cls_, workflow, history):
        create_time = now()
        update_time = create_time + timedelta(hours=1)
        state = "a"
        scheduler = "b"
        handler = "c"
        uuid = uuid4()

        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.workflow = workflow
        obj.state = state
        obj.scheduler = scheduler
        obj.handler = handler
        obj.uuid = uuid
        obj.history = history

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.workflow_id == workflow.id
            assert stored_obj.state == state
            assert stored_obj.scheduler == scheduler
            assert stored_obj.handler == handler
            assert stored_obj.uuid == uuid
            assert stored_obj.history_id == history.id

    def test_relationships(
        self,
        session,
        cls_,
        workflow,
        history,
        workflow_invocation_output_dataset_association,
        workflow_invocation_output_dataset_collection_association,
        workflow_invocation_step,
        workflow_invocation_to_subworkflow_invocation_association_factory,
        workflow_request_input_parameter,
        workflow_request_input_step_parameter,
        workflow_request_step_state,
        workflow_request_to_input_dataset_association,
        workflow_request_to_input_dataset_collection_association,
        workflow_invocation_output_value,
    ):
        subworkflow_invocation_assoc = workflow_invocation_to_subworkflow_invocation_association_factory()

        obj = cls_()
        obj.workflow = workflow
        obj.history = history
        obj.input_parameters.append(workflow_request_input_parameter)
        obj.step_states.append(workflow_request_step_state)
        obj.input_step_parameters.append(workflow_request_input_step_parameter)
        obj.input_datasets.append(workflow_request_to_input_dataset_association)
        obj.input_dataset_collections.append(workflow_request_to_input_dataset_collection_association)
        obj.subworkflow_invocations.append(subworkflow_invocation_assoc)
        obj.steps.append(workflow_invocation_step)
        obj.output_dataset_collections.append(workflow_invocation_output_dataset_collection_association)
        obj.output_datasets.append(workflow_invocation_output_dataset_association)
        obj.output_values.append(workflow_invocation_output_value)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.workflow.id == workflow.id
            assert stored_obj.history.id == history.id

            assert collection_consists_of_objects(stored_obj.input_parameters, workflow_request_input_parameter)
            assert collection_consists_of_objects(stored_obj.step_states, workflow_request_step_state)
            assert collection_consists_of_objects(
                stored_obj.input_step_parameters, workflow_request_input_step_parameter
            )
            assert collection_consists_of_objects(
                stored_obj.input_datasets, workflow_request_to_input_dataset_association
            )
            assert collection_consists_of_objects(
                stored_obj.input_dataset_collections,
                workflow_request_to_input_dataset_collection_association,
            )
            assert collection_consists_of_objects(stored_obj.subworkflow_invocations, subworkflow_invocation_assoc)
            assert collection_consists_of_objects(stored_obj.steps, workflow_invocation_step)
            assert collection_consists_of_objects(
                stored_obj.output_dataset_collections,
                workflow_invocation_output_dataset_collection_association,
            )
            assert collection_consists_of_objects(
                stored_obj.output_datasets,
                workflow_invocation_output_dataset_association,
            )
            assert collection_consists_of_objects(stored_obj.output_values, workflow_invocation_output_value)

        delete_from_database(session, subworkflow_invocation_assoc)


class TestWorkflowInvocationOutputDatasetAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "workflow_invocation_output_dataset_association"

    def test_columns(
        self,
        session,
        cls_,
        workflow_invocation,
        workflow_step,
        history_dataset_association,
        workflow_output,
    ):
        obj = cls_()
        obj.workflow_invocation = workflow_invocation
        obj.workflow_step = workflow_step
        obj.dataset = history_dataset_association
        obj.workflow_output = workflow_output

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.workflow_invocation_id == workflow_invocation.id
            assert stored_obj.workflow_step_id == workflow_step.id
            assert stored_obj.dataset_id == history_dataset_association.id
            assert stored_obj.workflow_output_id == workflow_output.id

    def test_relationships(
        self,
        session,
        cls_,
        workflow_invocation,
        workflow_step,
        history_dataset_association,
        workflow_output,
    ):
        obj = cls_()
        obj.workflow_invocation = workflow_invocation
        obj.workflow_step = workflow_step
        obj.dataset = history_dataset_association
        obj.workflow_output = workflow_output

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.workflow_invocation.id == workflow_invocation.id
            assert stored_obj.workflow_step.id == workflow_step.id
            assert stored_obj.dataset.id == history_dataset_association.id
            assert stored_obj.workflow_output.id == workflow_output.id


class TestWorkflowInvocationOutputDatasetCollectionAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "workflow_invocation_output_dataset_collection_association"

    def test_columns(
        self,
        session,
        cls_,
        workflow_invocation,
        workflow_step,
        history_dataset_collection_association,
        workflow_output,
    ):
        obj = cls_()
        obj.workflow_invocation = workflow_invocation
        obj.workflow_step = workflow_step
        obj.dataset_collection = history_dataset_collection_association
        obj.workflow_output = workflow_output

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.workflow_invocation_id == workflow_invocation.id
            assert stored_obj.workflow_step_id == workflow_step.id
            assert stored_obj.dataset_collection_id == history_dataset_collection_association.id
            assert stored_obj.workflow_output_id == workflow_output.id

    def test_relationships(
        self,
        session,
        cls_,
        workflow_invocation,
        workflow_step,
        history_dataset_collection_association,
        workflow_output,
    ):
        obj = cls_()
        obj.workflow_invocation = workflow_invocation
        obj.workflow_step = workflow_step
        obj.dataset_collection = history_dataset_collection_association
        obj.workflow_output = workflow_output

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.workflow_invocation.id == workflow_invocation.id
            assert stored_obj.workflow_step.id == workflow_step.id
            assert stored_obj.dataset_collection.id == history_dataset_collection_association.id
            assert stored_obj.workflow_output.id == workflow_output.id


class TestWorkflowInvocationOutputValue(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "workflow_invocation_output_value"

    def test_columns(
        self,
        session,
        cls_,
        workflow_invocation,
        workflow_step,
        workflow_output,
    ):
        value = "a"
        obj = cls_()
        obj.workflow_invocation = workflow_invocation
        obj.workflow_step = workflow_step
        obj.workflow_output = workflow_output
        obj.value = value

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.workflow_invocation_id == workflow_invocation.id
            assert stored_obj.workflow_step_id == workflow_step.id
            assert stored_obj.workflow_output_id == workflow_output.id
            assert stored_obj.value == value

    def test_relationships(
        self,
        session,
        cls_,
        workflow_invocation,
        workflow_step,
        workflow_output,
        workflow_invocation_step,
    ):
        # setup workflow_invocation_step to test the workflow_invocation_step attribute
        workflow_invocation_step.workflow_invocation = workflow_invocation
        workflow_invocation_step.workflow_step = workflow_step
        persist(session, workflow_invocation_step)

        obj = cls_()
        add_object_to_object_session(obj, workflow_invocation)
        obj.workflow_invocation = workflow_invocation
        obj.workflow_step = workflow_step
        obj.workflow_output = workflow_output

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.workflow_invocation.id == workflow_invocation.id
            assert stored_obj.workflow_step.id == workflow_step.id
            assert stored_obj.workflow_output.id == workflow_output.id
            assert stored_obj.workflow_invocation_step[0].id == workflow_invocation_step.id

        delete_from_database(session, [workflow_invocation_step])


class TestWorkflowInvocationStep(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "workflow_invocation_step"

    def test_columns(
        self,
        session,
        cls_,
        workflow_invocation,
        workflow_step,
        job,
        implicit_collection_jobs,
    ):
        create_time = now()
        update_time = create_time + timedelta(hours=1)
        state, action = "a", "b"

        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.workflow_invocation = workflow_invocation
        obj.workflow_step = workflow_step
        obj.state = state
        obj.job = job
        obj.implicit_collection_jobs = implicit_collection_jobs
        obj.action = action

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.workflow_invocation_id == workflow_invocation.id
            assert stored_obj.workflow_step_id == workflow_step.id
            assert stored_obj.state == state
            assert stored_obj.job_id == job.id
            assert stored_obj.implicit_collection_jobs_id == implicit_collection_jobs.id
            assert stored_obj.action == action

    def test_relationships(
        self,
        session,
        cls_,
        workflow_invocation,
        workflow_step,
        job,
        implicit_collection_jobs,
        workflow_invocation_step_output_dataset_collection_association,
        workflow_invocation_step_output_dataset_association,
        workflow_invocation_output_value,
    ):
        # setup workflow_invocation_output_value to test the output_value attribute
        output_value = workflow_invocation_output_value
        output_value.workflow_invocation = workflow_invocation
        output_value.workflow_step = workflow_step
        persist(session, output_value)

        obj = cls_()
        add_object_to_object_session(obj, workflow_invocation)
        obj.workflow_invocation = workflow_invocation
        obj.workflow_step = workflow_step
        obj.job = job
        obj.implicit_collection_jobs = implicit_collection_jobs
        obj.output_dataset_collections.append(workflow_invocation_step_output_dataset_collection_association)
        obj.output_datasets.append(workflow_invocation_step_output_dataset_association)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.workflow_invocation.id == workflow_invocation.id
            assert stored_obj.workflow_step.id == workflow_step.id
            assert stored_obj.job.id == job.id
            assert stored_obj.implicit_collection_jobs.id == implicit_collection_jobs.id
            assert collection_consists_of_objects(
                stored_obj.output_dataset_collections,
                workflow_invocation_step_output_dataset_collection_association,
            )
            assert collection_consists_of_objects(
                stored_obj.output_datasets,
                workflow_invocation_step_output_dataset_association,
            )
            assert stored_obj.output_value.id == workflow_invocation_output_value.id

    def test_subworkflow_invocation_attribute(
        self,
        session,
        cls_,
        workflow_step,
        workflow_invocation_to_subworkflow_invocation_association_factory,
        workflow_invocation_factory,
    ):
        # use defaults to create 2 workflows
        workflow_invocation1 = workflow_invocation_factory()
        workflow_invocation2 = workflow_invocation_factory()  # this is the subworkflow invocation

        # store to retrieve object ids
        persist(session, workflow_invocation1)
        persist(session, workflow_invocation2)
        persist(session, workflow_step)

        # setup assoc object and store
        assoc = workflow_invocation_to_subworkflow_invocation_association_factory()
        assoc.workflow_invocation_id = workflow_invocation1.id
        assoc.subworkflow_invocation_id = workflow_invocation2.id
        assoc.workflow_step_id = workflow_step.id
        persist(session, assoc)

        # setup main object under test
        obj = cls_()
        obj.workflow_invocation = workflow_invocation1
        obj.workflow_step = workflow_step

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.subworkflow_invocation_id == workflow_invocation2.id

        # finish cleanup
        persisted = [workflow_invocation1, workflow_invocation2, workflow_step, assoc]
        delete_from_database(session, persisted)


class TestWorkflowInvocationStepOutputDatasetAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "workflow_invocation_step_output_dataset_association"

    def test_columns(self, session, cls_, workflow_invocation_step, history_dataset_association):
        output_name = "a"
        obj = cls_()
        obj.workflow_invocation_step = workflow_invocation_step
        obj.dataset = history_dataset_association
        obj.output_name = output_name

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.workflow_invocation_step_id == workflow_invocation_step.id
            assert stored_obj.dataset_id == history_dataset_association.id
            assert stored_obj.output_name == output_name

    def test_relationships(self, session, cls_, workflow_invocation_step, history_dataset_association):
        obj = cls_()
        obj.workflow_invocation_step = workflow_invocation_step
        obj.dataset = history_dataset_association

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.workflow_invocation_step.id == workflow_invocation_step.id
            assert stored_obj.dataset.id == history_dataset_association.id


class TestWorkflowInvocationStepOutputDatasetCollectionAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "workflow_invocation_step_output_dataset_collection_association"

    def test_columns(
        self,
        session,
        cls_,
        workflow_invocation_step,
        workflow_step,
        history_dataset_collection_association,
    ):
        output_name = "a"
        obj = cls_()
        obj.workflow_invocation_step = workflow_invocation_step
        obj.workflow_step_id = workflow_step.id
        obj.dataset_collection = history_dataset_collection_association
        obj.output_name = output_name

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.workflow_invocation_step_id == workflow_invocation_step.id
            assert stored_obj.workflow_step_id == workflow_step.id
            assert stored_obj.dataset_collection_id == history_dataset_collection_association.id
            assert stored_obj.output_name == output_name

    def test_relationships(
        self,
        session,
        cls_,
        workflow_invocation_step,
        history_dataset_collection_association,
    ):
        obj = cls_()
        obj.workflow_invocation_step = workflow_invocation_step
        obj.dataset_collection = history_dataset_collection_association

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.workflow_invocation_step.id == workflow_invocation_step.id
            assert stored_obj.dataset_collection.id == history_dataset_collection_association.id


class TestWorkflowInvocationToSubworkflowInvocationAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "workflow_invocation_to_subworkflow_invocation_association"

    def test_columns(
        self,
        session,
        cls_,
        workflow_invocation,
        workflow_step,
        workflow,
        workflow_invocation_factory,
    ):
        subworkflow_invocation = workflow_invocation_factory()
        subworkflow_invocation.workflow = workflow
        persist(session, subworkflow_invocation)

        obj = cls_()
        obj.workflow_invocation_id = workflow_invocation.id
        obj.subworkflow_invocation = subworkflow_invocation
        obj.workflow_step = workflow_step

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.workflow_invocation_id == workflow_invocation.id
            assert stored_obj.subworkflow_invocation_id == subworkflow_invocation.id
            assert stored_obj.workflow_step_id == workflow_step.id

        delete_from_database(session, subworkflow_invocation)

    def test_relationships(
        self,
        session,
        cls_,
        workflow_invocation,
        workflow_step,
        workflow_invocation_factory,
    ):
        parent_workflow_invocation = workflow_invocation_factory()
        persist(session, parent_workflow_invocation)

        obj = cls_()
        obj.subworkflow_invocation = workflow_invocation  # We need only 1 instance, so we use the fixture
        obj.workflow_step = workflow_step
        obj.parent_workflow_invocation = parent_workflow_invocation

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.subworkflow_invocation.id == workflow_invocation.id
            assert stored_obj.workflow_step.id == workflow_step.id
            assert stored_obj.parent_workflow_invocation.id == parent_workflow_invocation.id

        delete_from_database(session, parent_workflow_invocation)


class TestWorkflowOutput(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "workflow_output"

    def test_columns(self, session, cls_, workflow_step):
        output_name, label, uuid = "a", "b", uuid4()
        obj = cls_(workflow_step, output_name, label, uuid)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.workflow_step_id == workflow_step.id
            assert stored_obj.output_name == output_name
            assert stored_obj.label == label
            assert stored_obj.uuid == uuid

    def test_relationships(self, session, cls_, workflow_step):
        obj = cls_(workflow_step)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.workflow_step.id == workflow_step.id


class TestWorkflowRequestInputParameter(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "workflow_request_input_parameters"

    def test_columns(self, session, cls_, workflow_invocation):
        name, value, type = "a", "b", "c"
        obj = cls_()
        obj.name = name
        obj.value = value
        obj.type = type
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


class TestWorkflowRequestInputStepParameter(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "workflow_request_input_step_parameter"

    def test_columns(self, session, cls_, workflow_step, workflow_invocation):
        parameter_value = "a"
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
        assert cls_.__tablename__ == "workflow_request_step_states"

    def test_columns(self, session, cls_, workflow_step, workflow_invocation):
        value = "a"
        obj = cls_()
        obj.workflow_step = workflow_step
        obj.value = value
        obj.workflow_invocation = workflow_invocation

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.workflow_invocation_id == workflow_invocation.id
            assert stored_obj.workflow_step_id == workflow_step.id
            assert stored_obj.value == value

    def test_relationships(self, session, cls_, workflow_step, workflow_invocation):
        obj = cls_()
        obj.workflow_step = workflow_step
        obj.workflow_invocation = workflow_invocation

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.workflow_invocation.id == workflow_invocation.id
            assert stored_obj.workflow_step.id == workflow_step.id


class TestWorkflowRequestToInputDatasetAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "workflow_request_to_input_dataset"

    def test_columns(
        self,
        session,
        cls_,
        workflow_step,
        workflow_invocation,
        history_dataset_association,
    ):
        name = "a"
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

    def test_relationships(
        self,
        session,
        cls_,
        workflow_step,
        workflow_invocation,
        history_dataset_association,
    ):
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
        assert cls_.__tablename__ == "workflow_request_to_input_collection_dataset"

    def test_columns(
        self,
        session,
        cls_,
        workflow_step,
        workflow_invocation,
        history_dataset_collection_association,
    ):
        name = "a"
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
        history_dataset_collection_association,
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


class TestWorkflowStep(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "workflow_step"

    def test_columns(self, session, cls_, workflow, dynamic_tool, workflow_factory):
        create_time = now()
        update_time = create_time + timedelta(hours=1)
        type = "a"
        tool_id = "b"
        tool_version = "c"
        tool_inputs = "d"
        tool_errors = "e"
        position = "f"
        config = "g"
        order_index = "h"
        label = "k"
        uuid = uuid4()

        subworkflow = workflow_factory()
        persist(session, subworkflow)

        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.workflow = workflow
        obj.subworkflow = subworkflow
        obj.dynamic_tool = dynamic_tool
        obj.type = type
        obj.tool_id = tool_id
        obj.tool_version = tool_version
        obj.tool_inputs = tool_inputs
        obj.tool_errors = tool_errors
        obj.position = position
        obj.config = config
        obj.order_index = order_index
        obj.label = label
        obj.uuid = uuid

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.workflow_id == workflow.id
            assert stored_obj.subworkflow_id == subworkflow.id
            assert stored_obj.dynamic_tool_id == dynamic_tool.id
            assert stored_obj.type == type
            assert stored_obj.tool_id == tool_id
            assert stored_obj.tool_version == tool_version
            assert stored_obj.tool_inputs == tool_inputs
            assert stored_obj.tool_errors == tool_errors
            assert stored_obj.position == position
            assert stored_obj.config == config
            assert stored_obj.order_index == order_index
            assert stored_obj.uuid == uuid
            assert stored_obj.label == label

        delete_from_database(session, subworkflow)

    def test_relationships(
        self,
        session,
        cls_,
        workflow,
        dynamic_tool,
        workflow_factory,
        workflow_step_connection_factory,
    ):
        subworkflow = workflow_factory()
        workflow_step_connection_in = workflow_step_connection_factory()
        workflow_step_connection_out = workflow_step_connection_factory()
        persist(session, subworkflow)
        persist(session, workflow_step_connection_in)
        persist(session, workflow_step_connection_out)

        obj = cls_()
        obj.workflow = workflow
        obj.subworkflow = subworkflow
        obj.dynamic_tool = dynamic_tool
        obj.output_connections.append(workflow_step_connection_out)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.workflow.id == workflow.id
            assert stored_obj.subworkflow.id == subworkflow.id
            assert stored_obj.dynamic_tool.id == dynamic_tool.id
            assert collection_consists_of_objects(stored_obj.output_connections, workflow_step_connection_out)

        persisted = [
            subworkflow,
            workflow_step_connection_in,
            workflow_step_connection_out,
        ]
        delete_from_database(session, persisted)


class TestWorkflowStepAnnotationAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "workflow_step_annotation_association"
        assert has_index(cls_.__table__, ("annotation",))

    def test_columns(self, session, cls_, workflow_step, user):
        annotation = "a"
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


class TestWorkflowStepConnection(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "workflow_step_connection"

    def test_columns(
        self,
        session,
        cls_,
        workflow_step_input,
        workflow_step,
        workflow,
        workflow_step_factory,
    ):
        output_name = "a"

        output_workflow_step = workflow_step_factory()
        output_workflow_step.workflow = workflow
        persist(session, output_workflow_step)

        obj = cls_()
        obj.output_step = output_workflow_step
        obj.input_step_input = workflow_step_input
        obj.output_name = output_name
        obj.input_subworkflow_step = workflow_step

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.output_step_id == output_workflow_step.id
            assert stored_obj.input_step_input_id == workflow_step_input.id
            assert stored_obj.output_name == output_name
            assert stored_obj.input_subworkflow_step_id == workflow_step.id

        delete_from_database(session, [output_workflow_step])

    def test_relationships(
        self,
        session,
        cls_,
        workflow_step_input,
        workflow_step,
        workflow,
        workflow_step_factory,
    ):
        output_workflow_step = workflow_step_factory()
        output_workflow_step.workflow = workflow
        persist(session, output_workflow_step)

        obj = cls_()
        obj.output_step = output_workflow_step
        obj.input_step_input = workflow_step_input
        obj.input_subworkflow_step = workflow_step

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.output_step.id == output_workflow_step.id
            assert stored_obj.input_step_input.id == workflow_step_input.id
            assert stored_obj.input_subworkflow_step.id == workflow_step.id

        delete_from_database(session, [output_workflow_step])


class TestWorkflowStepInput(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "workflow_step_input"
        assert has_index(cls_.__table__, ("workflow_step_id", "name"))

    def test_columns(self, session, cls_, workflow_step):
        name = "a"
        merge_type = "b"
        scatter_type = "c"
        value_from = "d"
        value_from_type = "e"
        default_value = "f"
        default_value_set = True
        runtime_value = True

        obj = cls_(workflow_step)
        obj.name = name
        obj.merge_type = merge_type
        obj.scatter_type = scatter_type
        obj.value_from = value_from
        obj.value_from_type = value_from_type
        obj.default_value = default_value
        obj.default_value_set = default_value_set
        obj.runtime_value = runtime_value

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.workflow_step_id == workflow_step.id
            assert stored_obj.name == name
            assert stored_obj.merge_type == merge_type
            assert stored_obj.scatter_type == scatter_type
            assert stored_obj.value_from == value_from
            assert stored_obj.value_from_type == value_from_type
            assert stored_obj.default_value == default_value
            assert stored_obj.default_value_set == default_value_set
            assert stored_obj.runtime_value == runtime_value

    def test_relationships(self, session, cls_, workflow_step, workflow_step_connection):
        obj = cls_(workflow_step)
        obj.connections.append(workflow_step_connection)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.workflow_step_id == workflow_step.id
            assert collection_consists_of_objects(stored_obj.connections, workflow_step_connection)


class TestWorkflowStepTagAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "workflow_step_tag_association"

    def test_columns(self, session, cls_, workflow_step, tag, user):
        user_tname, value, user_value = "a", "b", "c"
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


# Misc. helper fixtures.

# When enabled, this fixture auto-runs before each test and any unscoped fixtures
# (except session and model on which it depends) and verifies that all model
# tables in the database are empty. Thus, it ensures that a test is not affected
# by data leftover from a previous test run.
# It is expensive: it executes N statements of the form `SELECT count(*) FROM Foo`
# where N = |models under test| * |tests| = approx. 68K. This increases test
# execution time by approx. 350% (on my desktop 4 sec. vs. 14 sec.). It only
# verifies that the tests are written correctly, so it can be disabled by
# default. To enable it (which may be useful for debugging a test), add
# `autouse=True` to its decorator (see commented out line)
#
# @pytest.fixture(autouse=True)
@pytest.fixture()
def ensure_database_is_empty(session):
    """
    Auto-runs before each test and any unscoped fixtures, except session and model on
    which it depends. Verifies that all model tables in the database are empty. This
    ensures that a test is not affected by data leftover from a previous test run.
    For fixture instantiation order, see:
    https://docs.pytest.org/en/6.2.x/fixture.html#fixture-instantiation-order
    """
    # Created indirectrly (via db trigger and at Job instantiation): can't cleanup up automatically
    exclude = ["HistoryAudit", "JobStateHistory"]
    models = (cls_ for cls_ in model.__dict__.values() if hasattr(cls_, "__mapper__") and cls_.__name__ not in exclude)
    # For each mapped class, check that the database table to which it is mapped is empty
    for m in models:
        stmt = select(func.count()).select_from(m)
        result = session.execute(stmt).scalar()
        assert result == 0


# Test helpers
def _run_average_rating_test(session, obj, user, obj_rating_association_factory):
    # obj has been expunged; to access its deferred properties,
    # it needs to be added back to the session.
    session.add(obj)
    assert obj.average_rating is None  # With no ratings, we expect None.
    # Create ratings
    to_cleanup = []
    for rating in (1, 2, 3, 4, 5):
        obj_rating_assoc = obj_rating_association_factory(user, obj, rating)
        persist(session, obj_rating_assoc)
        to_cleanup.append(obj_rating_assoc)
    assert obj.average_rating == 3.0  # Expect average after ratings added.
    # Cleanup: remove ratings from database
    delete_from_database(session, to_cleanup)
