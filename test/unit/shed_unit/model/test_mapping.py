from datetime import (
    datetime,
    timedelta,
)

import pytest
from sqlalchemy import (
    func,
    select,
)

import tool_shed.webapp.model.mapping as mapping
from ...data.model.mapping.testing_utils import (
    collection_consists_of_objects,
    get_unique_value,
    has_unique_constraint,
)
from ...data.model.testing_utils import (
    dbcleanup,
    dbcleanup_wrapper,
    delete_from_database,
    get_stored_obj,
)


class BaseTest:
    @pytest.fixture
    def cls_(self, model):
        """
        Return class under test.
        Assumptions: if the class under test is Foo, then the class grouping
        the tests should be a subclass of BaseTest, named TestFoo.
        """
        prefix = len("Test")
        class_name = self.__class__.__name__[prefix:]
        return getattr(model, class_name)


class TestAPIKeys(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "api_keys"

    def test_columns(self, session, cls_, user):
        create_time, user_id, key = datetime.now(), user.id, get_unique_value()
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


class TestCategory(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "category"

    def test_columns(self, session, cls_):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        name, description, deleted = get_unique_value(), "b", True

        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.name = name
        obj.description = description
        obj.deleted = deleted

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.name == name
            assert stored_obj.description == description
            assert stored_obj.deleted == deleted

    def test_relationships(self, session, cls_, repository_category_association):
        obj = cls_()
        obj.name = get_unique_value()
        obj.repositories.append(repository_category_association)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.repositories == [repository_category_association]


class TestComponent(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "component"

    def test_columns(self, session, cls_):
        name, description = "a", "b"
        obj = cls_(name=name, description=description)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.name == name
            assert stored_obj.description == description


class TestComponentReview(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "component_review"

    def test_columns(self, session, cls_, repository_review, component):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        comment = "a"
        private = True
        approved = "b"
        rating = 1
        deleted = True

        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.repository_review = repository_review
        obj.component = component
        obj.comment = comment
        obj.private = private
        obj.approved = approved
        obj.rating = rating
        obj.deleted = deleted

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.repository_review_id == repository_review.id
            assert stored_obj.component_id == component.id
            assert stored_obj.comment == comment
            assert stored_obj.private == private
            assert stored_obj.approved == approved
            assert stored_obj.rating == rating
            assert stored_obj.deleted == deleted

    def test_relationships(self, session, cls_, repository_review, component):
        obj = cls_()
        obj.repository_review = repository_review
        obj.component = component

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.repository_review.id == repository_review.id
            assert stored_obj.component.id == component.id


class TestGalaxySession(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "galaxy_session"

    def test_columns(self, session, cls_, user, galaxy_session):

        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        remote_host = "a"
        remote_addr = "b"
        referer = "c"
        session_key = get_unique_value()
        is_valid = True
        last_action = update_time + timedelta(hours=1)

        obj = cls_(user=user, prev_session_id=galaxy_session.id)

        obj.create_time = create_time
        obj.update_time = update_time
        obj.remote_host = remote_host
        obj.remote_addr = remote_addr
        obj.referer = referer
        obj.session_key = session_key
        obj.is_valid = is_valid
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
            assert stored_obj.session_key == session_key
            assert stored_obj.is_valid == is_valid
            assert stored_obj.prev_session_id == galaxy_session.id
            assert stored_obj.last_action == last_action

    def test_relationships(self, session, cls_, user):
        obj = cls_(user=user)
        obj.session_key = get_unique_value()

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.user.id == user.id


class TestGroup(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "galaxy_group"

    def test_columns(self, session, cls_):
        create_time = datetime.now()
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
        group_role_association,
        user_group_association,
    ):
        obj = cls_(name=get_unique_value())
        obj.roles.append(group_role_association)
        obj.users.append(user_group_association)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.roles == [group_role_association]
            assert stored_obj.users == [user_group_association]


class TestGroupRoleAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "group_role_association"

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


class TestPasswordResetToken(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "password_reset_token"

    def test_columns_and_relationships(self, session, cls_, user):
        token = get_unique_value()
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


class TestRepository(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "repository"

    def test_columns(self, session, cls_, user):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        name = "a"
        type = "b"
        remote_repository_url = "c"
        homepage_url = "d"
        description = "e"
        long_description = "f"
        private = True
        deleted = True
        email_alerts = False
        times_downloaded = 1
        deprecated = True

        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.name = name
        obj.type = type
        obj.remote_repository_url = remote_repository_url
        obj.homepage_url = homepage_url
        obj.description = description
        obj.long_description = long_description
        obj.user = user
        obj.private = private
        obj.deleted = deleted
        obj.email_alerts = email_alerts
        obj.times_downloaded = times_downloaded
        obj.deprecated = deprecated

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.name == name
            assert stored_obj.type == type
            assert stored_obj.remote_repository_url == remote_repository_url
            assert stored_obj.homepage_url == homepage_url
            assert stored_obj.description == description
            assert stored_obj.long_description == long_description
            assert stored_obj.user_id == user.id
            assert stored_obj.private == private
            assert stored_obj.deleted == deleted
            assert stored_obj.email_alerts == email_alerts
            assert stored_obj.times_downloaded == times_downloaded
            assert stored_obj.deprecated == deprecated
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.name == name
            assert stored_obj.description == description
            assert stored_obj.deleted == deleted

    def test_relationships(
        self,
        session,
        cls_,
        repository_category_association,
        repository_rating_association,
        repository_metadata_factory,
        repository_role_association,
        repository_review_factory,
        user,
        user_factory,
    ):
        obj = cls_()
        obj.user = user
        obj.categories.append(repository_category_association)
        obj.ratings.append(repository_rating_association)
        obj.roles.append(repository_role_association)

        reviewer1 = user_factory()
        review1 = repository_review_factory()
        review1.user = reviewer1
        review1.repository = obj

        reviewer2 = user_factory()
        review2 = repository_review_factory()
        review2.user = reviewer2
        review2.repository = obj

        metadata1 = repository_metadata_factory()
        metadata1.repository = obj
        metadata1.downloadable = False

        metadata2 = repository_metadata_factory()
        metadata2.repository = obj
        metadata2.downloadable = True

        session.add_all([metadata1, metadata2])

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.user.id == user.id
            assert stored_obj.categories == [repository_category_association]
            assert stored_obj.ratings == [repository_rating_association]
            assert stored_obj.roles == [repository_role_association]
            assert collection_consists_of_objects(stored_obj.reviews, review1, review2)
            assert collection_consists_of_objects(stored_obj.reviewers, reviewer1, reviewer2)
            assert collection_consists_of_objects(stored_obj.metadata_revisions, metadata1, metadata2)
            assert stored_obj.downloadable_revisions == [metadata2]

        delete_from_database(session, [reviewer1, reviewer2, review1, review2, metadata1, metadata2])


class TestRepositoryCategoryAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "repository_category_association"

    def test_columns(self, session, cls_, repository, category):
        obj = cls_(repository=repository, category=category)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.repository_id == repository.id
            assert stored_obj.category_id == category.id

    def test_relationships(self, session, cls_, repository, category):
        obj = cls_(repository=repository, category=category)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.repository.id == repository.id
            assert stored_obj.category.id == category.id


class TestRepositoryMetadata(BaseTest):
    def test_table(self, cls_):
        assert cls_.table.name == "repository_metadata"

    def test_columns(self, session, cls_, repository):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        changeset_revision = "a"
        numeric_revision = 1
        metadata = "b"
        tool_versions = "c"
        malicious = True
        downloadable = False
        missing_test_components = True
        has_repository_dependencies = True
        includes_datatypes = True
        includes_tools = True
        includes_tool_dependencies = True
        includes_workflows = True

        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.repository = repository
        obj.changeset_revision = changeset_revision
        obj.numeric_revision = numeric_revision
        obj.metadata = metadata
        obj.tool_versions = tool_versions
        obj.malicious = malicious
        obj.downloadable = downloadable
        obj.missing_test_components = missing_test_components
        obj.has_repository_dependencies = has_repository_dependencies
        obj.includes_datatypes = includes_datatypes
        obj.includes_tools = includes_tools
        obj.includes_tool_dependencies = includes_tool_dependencies
        obj.includes_workflows = includes_workflows

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.repository_id == repository.id
            assert stored_obj.changeset_revision == changeset_revision
            assert stored_obj.numeric_revision == numeric_revision
            assert stored_obj.metadata == metadata
            assert stored_obj.tool_versions == tool_versions
            assert stored_obj.malicious == malicious
            assert stored_obj.downloadable == downloadable
            assert stored_obj.missing_test_components == missing_test_components
            assert stored_obj.has_repository_dependencies == has_repository_dependencies
            assert stored_obj.includes_datatypes == includes_datatypes
            assert stored_obj.includes_tools == includes_tools
            assert stored_obj.includes_tool_dependencies == includes_tool_dependencies
            assert stored_obj.includes_workflows == includes_workflows

    def test_relationships(
        self,
        session,
        cls_,
        repository,
        repository_review_factory,
        user,
    ):

        obj = cls_()
        obj.repository = repository
        obj.changeset_revision = "nonempty"

        # create 3 reviews
        review1 = repository_review_factory()
        review2 = repository_review_factory()
        review3 = repository_review_factory()

        # set the same user for all reviews
        review1.user = user
        review2.user = user
        review3.user = user

        # set the same repository for all reviews
        review1.repository = obj.repository
        review2.repository = obj.repository
        review3.repository = obj.repository

        # set the same changeset for reviews 1,2
        review1.changeset_revision = obj.changeset_revision
        review2.changeset_revision = obj.changeset_revision
        review3.changeset_revision = "something else"  # this won't be in reviews for this metadata

        # add to session
        session.add(review1)
        session.add(review2)
        session.add(review3)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.repository.id == repository.id
            assert collection_consists_of_objects(stored_obj.reviews, review1, review2)

        delete_from_database(session, [review1, review2, review3])


class TestRepositoryRatingAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "repository_rating_association"

    def test_columns(self, session, cls_, repository, user):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        rating = 1
        comment = "a"

        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.repository = repository
        obj.user = user
        obj.rating = rating
        obj.comment = comment

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.repository_id == repository.id
            assert stored_obj.user_id == user.id
            assert stored_obj.rating == rating
            assert stored_obj.comment == comment

    def test_relationships(self, session, cls_, repository, user):
        obj = cls_()
        obj.repository = repository
        obj.user = user

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.repository.id == repository.id
            assert stored_obj.user.id == user.id


class TestRepositoryReview(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "repository_review"

    def test_columns(self, session, cls_, repository, user):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        changeset_revision = "a"
        approved = "b"
        rating = 1
        deleted = True

        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.repository = repository
        obj.changeset_revision = changeset_revision
        obj.user = user
        obj.approved = approved
        obj.rating = rating
        obj.deleted = deleted

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.repository_id == repository.id
            assert stored_obj.changeset_revision == changeset_revision
            assert stored_obj.user_id == user.id
            assert stored_obj.approved == approved
            assert stored_obj.rating == rating
            assert stored_obj.deleted == deleted

    def test_relationships(
        self, session, cls_, repository, user, repository_metadata_factory, component_review_factory
    ):
        obj = cls_()
        changeset = "nonempty"
        obj.changeset_revision = changeset
        obj.repository = repository
        obj.user = user

        metadata1 = repository_metadata_factory()
        metadata2 = repository_metadata_factory()
        metadata1.repository = repository
        metadata2.repository = repository
        metadata1.changeset_revision = changeset
        metadata2.changeset_revision = "something else"

        component_review1 = component_review_factory()
        component_review1.repository_review = obj
        component_review1.deleted = False

        component_review2 = component_review_factory()
        component_review2.repository_review = obj
        component_review2.deleted = False
        component_review2.private = True

        session.add_all([metadata1, metadata2, component_review1, component_review2])

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.repository.id == repository.id
            assert stored_obj.user.id == user.id
            assert stored_obj.repository_metadata == metadata1
            assert collection_consists_of_objects(stored_obj.component_reviews, component_review1, component_review2)
            assert stored_obj.private_component_reviews == [component_review2]

        delete_from_database(session, [component_review1, component_review2, metadata1, metadata2])


class TestRepositoryRoleAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "repository_role_association"

    def test_columns(self, session, cls_, repository, role):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        obj = cls_(repository, role)
        obj.create_time = create_time
        obj.update_time = update_time

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.repository_id == repository.id
            assert stored_obj.role_id == role.id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time

    def test_relationships(self, session, cls_, repository, role):
        obj = cls_(repository, role)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.repository.id == repository.id
            assert stored_obj.role.id == role.id


class TestRole(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "role"

    def test_columns(self, session, cls_):
        name, description, type_, deleted = get_unique_value(), "b", cls_.types.SYSTEM, True
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
        repository_role_association,
        user_role_association,
        group_role_association_factory,
        group,
    ):
        name, description, type_ = get_unique_value(), "b", cls_.types.SYSTEM
        obj = cls_(name, description, type_)
        obj.repositories.append(repository_role_association)
        obj.users.append(user_role_association)

        gra = group_role_association_factory(group, obj)
        obj.groups.append(gra)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.repositories == [repository_role_association]
            assert stored_obj.users == [user_role_association]
            assert stored_obj.groups == [gra]

        delete_from_database(session, gra)


class TestTag(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "tag"
        assert has_unique_constraint(cls_.table, ("name",))

    def test_columns(self, session, cls_):
        parent_tag = cls_()
        type_, name = 1, get_unique_value()
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
            assert stored_obj.children == [child_tag]

        delete_from_database(session, [parent_tag, child_tag])


class TestUser(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "galaxy_user"

    def test_columns(self, session, cls_):
        create_time = datetime.now()
        update_time = create_time + timedelta(hours=1)
        email = get_unique_value()
        username = get_unique_value()
        password = "c"
        external = True
        new_repo_alert = True
        deleted = True
        purged = True

        obj = cls_()
        obj.create_time = create_time
        obj.update_time = update_time
        obj.email = email
        obj.username = username
        obj.password = password
        obj.external = external
        obj.new_repo_alert = new_repo_alert
        obj.deleted = deleted
        obj.purged = purged

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.id == obj_id
            assert stored_obj.create_time == create_time
            assert stored_obj.update_time == update_time
            assert stored_obj.email == email
            assert stored_obj.username == username
            assert stored_obj.password == password
            assert stored_obj.external == external
            assert stored_obj.new_repo_alert == new_repo_alert
            assert stored_obj.deleted == deleted
            assert stored_obj.purged == purged

    def test_relationships(
        self,
        session,
        cls_,
        repository,
        galaxy_session,
        api_keys,
        repository_review,
        role,
        group,
        password_reset_token,
        user_group_association,
        user_role_association,
        role_factory,
        user_role_association_factory,
    ):
        obj = cls_()
        obj.email = get_unique_value()
        obj.password = "a"
        obj.active_repositories.append(repository)
        obj.galaxy_sessions.append(galaxy_session)
        obj.api_keys.append(api_keys)
        obj.reset_tokens.append(password_reset_token)
        obj.groups.append(user_group_association)
        obj.repository_reviews.append(repository_review)

        _private_role = role_factory(name=obj.email)
        private_user_role = user_role_association_factory(obj, _private_role)
        obj.roles.append(private_user_role)

        _non_private_role = role_factory(name="a")
        non_private_user_role = user_role_association_factory(obj, _non_private_role)
        obj.roles.append(non_private_user_role)

        with dbcleanup(session, obj) as obj_id:
            stored_obj = get_stored_obj(session, cls_, obj_id)
            assert stored_obj.active_repositories == [repository]
            assert stored_obj.galaxy_sessions == [galaxy_session]
            assert stored_obj.api_keys == [api_keys]
            assert stored_obj.reset_tokens == [password_reset_token]
            assert stored_obj.groups == [user_group_association]
            assert stored_obj.repository_reviews == [repository_review]
            assert collection_consists_of_objects(stored_obj.roles, private_user_role, non_private_user_role)
            assert stored_obj.non_private_roles == [non_private_user_role]

        delete_from_database(session, [_private_role, _non_private_role, private_user_role, non_private_user_role])


class TestUserGroupAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "user_group_association"

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


class TestUserRoleAssociation(BaseTest):
    def test_table(self, cls_):
        assert cls_.__tablename__ == "user_role_association"

    def test_columns(self, session, cls_, user, role):
        create_time = datetime.now()
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


# Misc. helper fixtures.
@pytest.fixture(autouse=True)
def ensure_database_is_empty(session, model):
    """
    Auto-runs before each test and any unscoped fixtures, except session and model on
    which it depends. Verifies that all model tables in the database are empty. This
    ensures that a test is not affected by data leftover from a previous test run.
    For fixture instantiation order, see:
    https://docs.pytest.org/en/6.2.x/fixture.html#fixture-instantiation-order
    """
    models = (cls_ for cls_ in model.__dict__.values() if hasattr(cls_, "__mapper__"))
    # For each mapped class, check that the database table to which it is mapped is empty
    for m in models:
        stmt = select(func.count()).select_from(m)
        result = session.execute(stmt).scalar()
        assert result == 0


@pytest.fixture(scope="module")
def model():
    db_uri = "sqlite:///:memory:"
    return mapping.init("/tmp", db_uri, create_tables=True)


@pytest.fixture
def session(model):
    Session = model.session
    yield Session()
    Session.remove()  # Ensures we get a new session for each test


@pytest.fixture
def api_keys(model, session):
    instance = model.APIKeys(key=get_unique_value())
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def category(model, session):
    instance = model.Category(name=get_unique_value())
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def component(model, session):
    instance = model.Component()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def galaxy_session(model, session):
    instance = model.GalaxySession(session_key=get_unique_value())
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def group(model, session):
    instance = model.Group(name=get_unique_value())
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def group_role_association(model, session):
    instance = model.GroupRoleAssociation(None, None)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def password_reset_token(model, session, user):
    token = get_unique_value()
    instance = model.PasswordResetToken(user, token)
    where_clause = model.PasswordResetToken.token == token
    yield from dbcleanup_wrapper(session, instance, where_clause)


@pytest.fixture
def repository(model, session):
    instance = model.Repository()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def repository_metadata(model, session):
    instance = model.RepositoryMetadata()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def repository_review(model, session, user):
    instance = model.RepositoryReview()
    instance.user = user
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def repository_category_association(model, session, repository, category):
    instance = model.RepositoryCategoryAssociation(repository, category)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def repository_rating_association(model, session):
    instance = model.RepositoryRatingAssociation()
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def repository_role_association(model, session, repository, role):
    instance = model.RepositoryRoleAssociation(repository, role)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def role(model, session):
    instance = model.Role(name=get_unique_value())
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def user(model, session):
    instance = model.User(email=get_unique_value(), password="password")
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def user_group_association(model, session, user, group):
    instance = model.UserGroupAssociation(user, group)
    yield from dbcleanup_wrapper(session, instance)


@pytest.fixture
def user_role_association(model, session, user, role):
    instance = model.UserRoleAssociation(user, role)
    yield from dbcleanup_wrapper(session, instance)


# Fixtures yielding factory functions.


@pytest.fixture
def component_review_factory(model):
    def make_instance(*args, **kwds):
        return model.ComponentReview(*args, **kwds)

    return make_instance


@pytest.fixture
def group_role_association_factory(model):
    def make_instance(*args, **kwds):
        return model.GroupRoleAssociation(*args, **kwds)

    return make_instance


@pytest.fixture
def repository_metadata_factory(model):
    def make_instance(*args, **kwds):
        return model.RepositoryMetadata(*args, **kwds)

    return make_instance


@pytest.fixture
def repository_review_factory(model):
    def make_instance(*args, **kwds):
        return model.RepositoryReview(*args, **kwds)

    return make_instance


@pytest.fixture
def role_factory(model):
    def make_instance(*args, **kwds):
        return model.Role(*args, **kwds)

    return make_instance


@pytest.fixture
def user_factory(model):
    def make_instance(*args, **kwds):
        user = model.User(*args, **kwds)
        user.email = get_unique_value()
        user.password = "a"
        return user

    return make_instance


@pytest.fixture
def user_role_association_factory(model):
    def make_instance(*args, **kwds):
        return model.UserRoleAssociation(*args, **kwds)

    return make_instance
