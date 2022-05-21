"""
See documentation + annotated examples for these tests in test_model_mapping.py.
"""

from datetime import (
    datetime,
    timedelta,
)

from galaxy.model import tool_shed_install as model
from .testing_utils import (
    AbstractBaseTest,
    collection_consists_of_objects,
)
from ..testing_utils import (
    dbcleanup,
    delete_from_database,
    get_plugin_full_name,
    get_stored_obj,
)

model_fixtures = get_plugin_full_name("mapping.testing_utils.tsi_model_fixtures")
pytest_plugins = [model_fixtures]


class BaseTest(AbstractBaseTest):
    def get_model(self):
        return model


class TestToolShedRepository(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "tool_shed_repository"

    def test_columns(self, session, cls_, repository):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        tool_shed = "a"
        name = "b"
        description = "c"
        owner = "d"
        installed_changeset_revision = "e"
        changeset_revision = "f"
        ctx_rev = "g"
        metadata_ = "h"
        includes_datatypes = True
        tool_shed_status = "i"
        deleted = True
        uninstalled = True
        dist_to_shed = True
        status = "j"
        error_message = "k"

        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.tool_shed = tool_shed
        obj.name = name
        obj.description = description
        obj.owner = owner
        obj.installed_changeset_revision = installed_changeset_revision
        obj.changeset_revision = changeset_revision
        obj.ctx_rev = ctx_rev
        obj.metadata_ = metadata_
        obj.includes_datatypes = includes_datatypes
        obj.tool_shed_status = tool_shed_status
        obj.deleted = deleted
        obj.uninstalled = uninstalled
        obj.dist_to_shed = dist_to_shed
        obj.status = status
        obj.error_message = error_message

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.tool_shed == tool_shed
            assert stored_obj.name == name
            assert stored_obj.description == description
            assert stored_obj.owner == owner
            assert stored_obj.installed_changeset_revision == installed_changeset_revision
            assert stored_obj.changeset_revision == changeset_revision
            assert stored_obj.ctx_rev == ctx_rev
            assert stored_obj.metadata_ == metadata_
            assert stored_obj.includes_datatypes == includes_datatypes
            assert stored_obj.tool_shed_status == tool_shed_status
            assert stored_obj.deleted == deleted
            assert stored_obj.uninstalled == uninstalled
            assert stored_obj.dist_to_shed == dist_to_shed
            assert stored_obj.status == status
            assert stored_obj.error_message == error_message

    def test_relationships(
        self,
        session,
        cls_,
        repository,
        tool_version,
        tool_dependency,
        repository_repository_dependency_association,
    ):
        obj = cls_()
        obj.tool_versions.append(tool_version)
        obj.tool_dependencies.append(tool_dependency)
        obj.required_repositories.append(repository_repository_dependency_association)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert collection_consists_of_objects(stored_obj.tool_versions, tool_version)
            assert collection_consists_of_objects(stored_obj.tool_dependencies, tool_dependency)
            assert collection_consists_of_objects(
                stored_obj.required_repositories, repository_repository_dependency_association
            )


class TestRepositoryRepositoryDependencyAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "repository_repository_dependency_association"

    def test_columns(self, session, cls_, repository, repository_dependency):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.repository = repository
        obj.repository_dependency = repository_dependency

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.tool_shed_repository_id == repository.id
            assert stored_obj.repository_dependency_id == repository_dependency.id

    def test_relationships(self, session, cls_, repository, repository_dependency):
        obj = cls_()
        obj.repository = repository
        obj.repository_dependency = repository_dependency

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.repository.id == repository.id
            assert stored_obj.repository_dependency.id == repository_dependency.id


class TestRepositoryDependency(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "repository_dependency"

    def test_columns(self, session, cls_, repository):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_(repository.id)
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.tool_shed_repository_id == repository.id

    def test_relationships(self, session, cls_, repository):
        obj = cls_(repository.id)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.repository.id == repository.id


class TestToolDependency(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "tool_dependency"

    def test_columns(self, session, cls_, repository):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        name, version, type, status, error_message = "a", "b", "c", "d", "e"
        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.tool_shed_repository_id = repository.id
        obj.name = name
        obj.version = version
        obj.type = type
        obj.status = status
        obj.error_message = error_message

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.tool_shed_repository_id == repository.id
            assert stored_obj.name == name
            assert stored_obj.version == version
            assert stored_obj.type == type
            assert stored_obj.status == status
            assert stored_obj.error_message == error_message

    def test_relationships(self, session, cls_, repository):
        obj = cls_()
        obj.tool_shed_repository = repository
        obj.status = "a"

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.tool_shed_repository.id == repository.id


class TestToolVersion(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "tool_version"

    def test_columns(self, session, cls_, repository):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        tool_id = "a"
        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.tool_id = tool_id
        obj.tool_shed_repository = repository

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.tool_id == tool_id
            assert stored_obj.tool_shed_repository_id == repository.id

    def test_relationships(self, session, cls_, repository, tool_version_association_factory, tool_version):
        # This test is non-standard because we must test associations that do not have relationships set up.
        # As a result, we need the object pkey in order to setup the test, which is why we have to manually
        # add obj to the session and flush it.
        obj = cls_()
        obj.tool_shed_repository = repository

        session.add(obj)
        session.flush()

        tool_version_assoc1 = tool_version_association_factory()
        tool_version_assoc1.tool_id = obj.id  # tool_version under test
        tool_version_assoc1.parent_id = tool_version.id  # some other tool_version

        tool_version_assoc2 = tool_version_association_factory()
        tool_version_assoc2.tool_id = tool_version.id  # some other tool_version
        tool_version_assoc2.parent_id = obj.id  # tool_version under test

        session.add(tool_version_assoc1)
        session.add(tool_version_assoc2)
        session.flush()

        stored_obj = get_stored_obj(session, cls_, obj.id)
        assert stored_obj.tool_shed_repository.id == repository.id
        assert collection_consists_of_objects(stored_obj.parent_tool_association, tool_version_assoc1)
        assert collection_consists_of_objects(stored_obj.child_tool_association, tool_version_assoc2)

        delete_from_database(session, [obj, tool_version_assoc1, tool_version_assoc2])


class TestToolVersionAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "tool_version_association"

    def test_columns(self, session, cls_, tool_version_factory):
        tool_version = tool_version_factory()
        parent_tool_version = tool_version_factory()

        session.add(tool_version)
        session.add(parent_tool_version)
        session.flush()

        obj = cls_()
        obj.tool_id = tool_version.id
        obj.parent_id = parent_tool_version.id

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.tool_id == tool_version.id
            assert stored_obj.parent_id == parent_tool_version.id

        delete_from_database(session, [tool_version, parent_tool_version])
