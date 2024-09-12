import pytest

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.model import (
    Group,
    Role,
    User,
)
from galaxy.model.security import GalaxyRBACAgent
from . import have_same_elements


@pytest.fixture
def make_user_and_role(session, make_user, make_role, make_user_role_association):
    """
    Each user created in Galaxy is assumed to have a private role, such that role.name == user.email.
    Since we are testing user/group/role associations here, to ensure the correct state of the test database,
    we need to ensure that a user is never created without a corresponding private role.
    Therefore, we use this fixture instead of make_user (which only creates a user).
    """

    def f(**kwd):
        user = make_user()
        private_role = make_role(name=user.email, type=Role.types.PRIVATE)
        make_user_role_association(user, private_role)
        return user, private_role

    return f


def test_private_user_role_assoc_not_affected_by_setting_user_roles(session, make_user_and_role):
    # Create user with a private role
    user, private_role = make_user_and_role()
    assert user.email == private_role.name
    verify_user_associations(user, [], [private_role])  # the only existing association is with the private role

    # Update users's email so it's no longer the same as the private role's name.
    user.email = user.email + "updated"
    session.add(user)
    session.commit()
    assert user.email != private_role.name

    # Delete user roles
    GalaxyRBACAgent(session).set_user_group_and_role_associations(user, role_ids=[])
    # association with private role is preserved
    verify_user_associations(user, [], [private_role])


def test_private_user_role_assoc_not_affected_by_setting_role_users(session, make_user_and_role):
    # Create user with a private role
    user, private_role = make_user_and_role()
    assert user.email == private_role.name
    verify_user_associations(user, [], [private_role])  # the only existing association is with the private role

    # Update users's email
    user.email = user.email + "updated"
    session.add(user)
    session.commit()
    assert user.email != private_role.name

    # Update role users
    GalaxyRBACAgent(session).set_role_user_and_group_associations(private_role, user_ids=[])
    # association of private role with user is preserved
    verify_role_associations(private_role, [user], [])


def test_cannot_assign_private_roles(session, make_user_and_role, make_role):
    user, private_role1 = make_user_and_role()
    _, private_role2 = make_user_and_role()
    new_role = make_role()
    verify_user_associations(user, [], [private_role1])  # the only existing association is with the private role

    # Try to assign 2 more roles: regular role + another private role
    GalaxyRBACAgent(session).set_user_group_and_role_associations(user, role_ids=[new_role.id, private_role2.id])
    # Only regular role has been added: other private role ignored; original private role still assigned
    verify_user_associations(user, [], [private_role1, new_role])


class TestSetGroupUserAndRoleAssociations:

    def test_add_associations_to_existing_group(self, session, make_user_and_role, make_role, make_group):
        """
        State: group exists in database, has no user and role associations.
        Action: add new associations.
        """
        group = make_group()
        users = [make_user_and_role()[0] for _ in range(5)]
        roles = [make_role() for _ in range(5)]

        # users and roles for creating associations
        users_to_add = [users[0], users[2], users[4]]
        user_ids = [u.id for u in users_to_add]
        roles_to_add = [roles[1], roles[3]]
        role_ids = [r.id for r in roles_to_add]

        # verify no preexisting associations
        verify_group_associations(group, [], [])

        # set associations
        GalaxyRBACAgent(session).set_group_user_and_role_associations(group, user_ids=user_ids, role_ids=role_ids)

        # verify new associations
        verify_group_associations(group, users_to_add, roles_to_add)

    def test_add_associations_to_new_group(self, session, make_user_and_role, make_role):
        """
        State: group does NOT exist in database, has no user and role associations.
        Action: add new associations.
        """
        group = Group()
        session.add(group)
        assert group.id is None  # group does not exist in database
        users = [make_user_and_role()[0] for _ in range(5)]  # type: ignore[unreachable]
        roles = [make_role() for _ in range(5)]

        # users and roles for creating associations
        users_to_add = [users[0], users[2], users[4]]
        user_ids = [u.id for u in users_to_add]
        roles_to_add = [roles[1], roles[3]]
        role_ids = [r.id for r in roles_to_add]

        # set associations
        GalaxyRBACAgent(session).set_group_user_and_role_associations(group, user_ids=user_ids, role_ids=role_ids)

        # verify new associations
        verify_group_associations(group, users_to_add, roles_to_add)

    def test_update_associations(
        self,
        session,
        make_user_and_role,
        make_role,
        make_group,
        make_user_group_association,
        make_group_role_association,
    ):
        """
        State: group exists in database AND has user and role associations.
        Action: update associations (add some/drop some).
        Expect: old associations are REPLACED by new associations.
        """
        group = make_group()
        users = [make_user_and_role()[0] for _ in range(5)]
        roles = [make_role() for _ in range(5)]

        # load and verify existing associations
        users_to_load = [users[0], users[2]]
        roles_to_load = [roles[1], roles[3]]
        for user in users_to_load:
            make_user_group_association(user, group)
        for role in roles_to_load:
            make_group_role_association(group, role)
        verify_group_associations(group, users_to_load, roles_to_load)

        # users and roles for creating new associations
        new_users_to_add = [users[0], users[1], users[3]]
        user_ids = [u.id for u in new_users_to_add]
        new_roles_to_add = [roles[2]]
        role_ids = [r.id for r in new_roles_to_add]

        # sanity check: ensure we are trying to change existing associations
        assert not have_same_elements(users_to_load, new_users_to_add)
        assert not have_same_elements(roles_to_load, new_roles_to_add)

        # set associations
        GalaxyRBACAgent(session).set_group_user_and_role_associations(group, user_ids=user_ids, role_ids=role_ids)

        # verify new associations
        verify_group_associations(group, new_users_to_add, new_roles_to_add)

    def test_drop_associations(
        self,
        session,
        make_user_and_role,
        make_role,
        make_group,
        make_user_group_association,
        make_group_role_association,
    ):
        """
        State: group exists in database AND has user and role associations.
        Action: drop all associations.
        """
        group = make_group()
        users = [make_user_and_role()[0] for _ in range(5)]
        roles = [make_role() for _ in range(5)]

        # load and verify existing associations
        users_to_load = [users[0], users[2]]
        roles_to_load = [roles[1], roles[3]]
        for user in users_to_load:
            make_user_group_association(user, group)
        for role in roles_to_load:
            make_group_role_association(group, role)
        verify_group_associations(group, users_to_load, roles_to_load)

        # drop associations
        GalaxyRBACAgent(session).set_group_user_and_role_associations(group, user_ids=[], role_ids=[])

        # verify associations dropped
        verify_group_associations(group, [], [])

    def test_invalid_user(self, session, make_user_and_role, make_role, make_group):
        """
        State: group exists in database, has no user and role associations.
        Action: try to add several associations, last one having an invalid user id.
        Expect: no associations are added, appropriate error is raised.
        """
        group = make_group()
        users = [make_user_and_role()[0] for _ in range(5)]

        # users for creating associations
        user_ids = [users[0].id, -1]  # first is valid, second is invalid

        # verify no preexisting associations
        assert len(group.users) == 0

        # try to set associations
        with pytest.raises(RequestParameterInvalidException):
            GalaxyRBACAgent(session).set_group_user_and_role_associations(group, user_ids=user_ids)

        # verify no change
        assert len(group.users) == 0

    def test_invalid_role(self, session, make_role, make_group):
        """
        state: group exists in database, has no user and role associations.
        action: try to add several associations, last one having an invalid role id.
        expect: no associations are added, appropriate error is raised.
        """
        group = make_group()
        roles = [make_role() for _ in range(5)]

        # roles for creating associations
        role_ids = [roles[0].id, -1]  # first is valid, second is invalid

        # verify no preexisting associations
        assert len(group.roles) == 0

        # try to set associations
        with pytest.raises(RequestParameterInvalidException):
            GalaxyRBACAgent(session).set_group_user_and_role_associations(group, role_ids=role_ids)

        # verify no change
        assert len(group.roles) == 0

    def test_duplicate_user(
        self,
        session,
        make_user_and_role,
        make_role,
        make_group,
        make_user_group_association,
        make_group_role_association,
    ):
        """
        State: group exists in database and has user and role associations.
        Action: try update user and role associations including a duplicate user
        Expect: error raised, no change is made to group users and group roles.
        """
        group = make_group()
        users = [make_user_and_role()[0] for _ in range(5)]
        roles = [make_role() for _ in range(5)]

        # load and verify existing associations
        users_to_load = [users[0], users[2]]
        roles_to_load = [roles[1], roles[3]]
        for user in users_to_load:
            make_user_group_association(user, group)
        for role in roles_to_load:
            make_group_role_association(group, role)
        verify_group_associations(group, users_to_load, roles_to_load)

        # users and roles for creating new associations
        new_users_to_add = users + [users[0]]  # include a duplicate user
        user_ids = [u.id for u in new_users_to_add]

        new_roles_to_add = roles  # NO duplice roles
        role_ids = [r.id for r in new_roles_to_add]

        # sanity check: ensure we are trying to change existing associations
        assert not have_same_elements(users_to_load, new_users_to_add)
        assert not have_same_elements(roles_to_load, new_roles_to_add)

        with pytest.raises(RequestParameterInvalidException):
            GalaxyRBACAgent(session).set_group_user_and_role_associations(group, user_ids=user_ids, role_ids=role_ids)

        # verify associations not updated
        verify_group_associations(group, users_to_load, roles_to_load)

    def test_duplicate_role(
        self,
        session,
        make_user_and_role,
        make_role,
        make_group,
        make_user_group_association,
        make_group_role_association,
    ):
        """
        State: group exists in database and has user and role associations.
        Action: try update user and role associations including a duplicate role
        Expect: error raised, no change is made to group users and group roles.
        """
        group = make_group()
        users = [make_user_and_role()[0] for _ in range(5)]
        roles = [make_role() for _ in range(5)]

        # load and verify existing associations
        users_to_load = [users[0], users[2]]
        roles_to_load = [roles[1], roles[3]]
        for user in users_to_load:
            make_user_group_association(user, group)
        for role in roles_to_load:
            make_group_role_association(group, role)
        verify_group_associations(group, users_to_load, roles_to_load)

        # users and roles for creating new associations
        new_users_to_add = users  # NO duplicate users
        user_ids = [u.id for u in new_users_to_add]

        new_roles_to_add = roles + [roles[0]]  # include a duplicate role
        role_ids = [r.id for r in new_roles_to_add]

        # sanity check: ensure we are trying to change existing associations
        assert not have_same_elements(users_to_load, new_users_to_add)
        assert not have_same_elements(roles_to_load, new_roles_to_add)

        with pytest.raises(RequestParameterInvalidException):
            GalaxyRBACAgent(session).set_group_user_and_role_associations(group, user_ids=user_ids, role_ids=role_ids)

        # verify associations not updated
        verify_group_associations(group, users_to_load, roles_to_load)


class TestSetUserGroupAndRoleAssociations:
    """
    Note: a user should always have a private role which is not affected
    by modifying a user's group associations or role associations.
    """

    def test_add_associations_to_existing_user(self, session, make_user_and_role, make_role, make_group):
        """
        State: user exists in database, has no group and only one private role association.
        Action: add new associations.
        """
        user, private_role = make_user_and_role()
        groups = [make_group() for _ in range(5)]
        roles = [make_role() for _ in range(5)]

        # groups and roles for creating associations
        groups_to_add = [groups[0], groups[2], groups[4]]
        group_ids = [g.id for g in groups_to_add]
        roles_to_add = [roles[1], roles[3]]
        role_ids = [r.id for r in roles_to_add]

        # verify preexisting associations
        verify_user_associations(user, [], [private_role])

        # set associations
        GalaxyRBACAgent(session).set_user_group_and_role_associations(user, group_ids=group_ids, role_ids=role_ids)

        # verify new associations
        verify_user_associations(user, groups_to_add, roles_to_add + [private_role])

    def test_add_associations_to_new_user(self, session, make_role, make_group):
        """
        State: user does NOT exist in database, has no group and role associations.
        Action: add new associations.
        """
        user = User(email="foo@foo.com", password="password")
        # We are not creating a private role and a user-role association with that role because that would result in
        # adding the user to the database before calling the method under test, whereas the test is intended to verify
        # correct processing of a user that has NOT been saved to the database.

        session.add(user)
        assert user.id is None  # user does not exist in database
        groups = [make_group() for _ in range(5)]  # type: ignore[unreachable]
        roles = [make_role() for _ in range(5)]

        # groups and roles for creating associations
        groups_to_add = [groups[0], groups[2], groups[4]]
        group_ids = [g.id for g in groups_to_add]
        roles_to_add = [roles[1], roles[3]]
        role_ids = [r.id for r in roles_to_add]

        # set associations
        GalaxyRBACAgent(session).set_user_group_and_role_associations(user, group_ids=group_ids, role_ids=role_ids)

        # verify new associations
        verify_user_associations(user, groups_to_add, roles_to_add)

    def test_update_associations(
        self,
        session,
        make_user_and_role,
        make_role,
        make_group,
        make_user_group_association,
        make_user_role_association,
    ):
        """
        State: user exists in database AND has group and role associations.
        Action: update associations (add some/drop some).
        Expect: old associations are REPLACED by new associations.
        """
        user, private_role = make_user_and_role()
        groups = [make_group() for _ in range(5)]
        roles = [make_role() for _ in range(5)]

        # load and verify existing associations
        groups_to_load = [groups[0], groups[2]]
        roles_to_load = [roles[1], roles[3]]
        for group in groups_to_load:
            make_user_group_association(user, group)
        for role in roles_to_load:
            make_user_role_association(user, role)
        verify_user_associations(user, groups_to_load, roles_to_load + [private_role])

        # groups and roles for creating new associations
        new_groups_to_add = [groups[0], groups[1], groups[3]]
        group_ids = [g.id for g in new_groups_to_add]
        new_roles_to_add = [roles[2]]
        role_ids = [r.id for r in new_roles_to_add]

        # sanity check: ensure we are trying to change existing associations
        assert not have_same_elements(groups_to_load, new_groups_to_add)
        assert not have_same_elements(roles_to_load, new_roles_to_add)

        # set associations
        GalaxyRBACAgent(session).set_user_group_and_role_associations(user, group_ids=group_ids, role_ids=role_ids)
        # verify new associations
        verify_user_associations(user, new_groups_to_add, new_roles_to_add + [private_role])

    def test_drop_associations(
        self,
        session,
        make_user_and_role,
        make_role,
        make_group,
        make_user_group_association,
        make_user_role_association,
    ):
        """
        State: user exists in database AND has group and role associations.
        Action: drop all associations.
        """
        user, private_role = make_user_and_role()
        groups = [make_group() for _ in range(5)]
        roles = [make_role() for _ in range(5)]

        # load and verify existing associations
        groups_to_load = [groups[0], groups[2]]
        roles_to_load = [roles[1], roles[3]]
        for group in groups_to_load:
            make_user_group_association(user, group)
        for role in roles_to_load:
            make_user_role_association(user, role)
        verify_user_associations(user, groups_to_load, roles_to_load + [private_role])

        # drop associations
        GalaxyRBACAgent(session).set_user_group_and_role_associations(user, group_ids=[], role_ids=[])

        # verify associations dropped
        verify_user_associations(user, [], [private_role])

    def test_invalid_group(self, session, make_user_and_role, make_group):
        """
        State: user exists in database, has no group and only one private role association.
        Action: try to add several associations, last one having an invalid group id.
        Expect: no associations are added, appropriate error is raised.
        """
        user, private_role = make_user_and_role()
        groups = [make_group() for _ in range(5)]

        # groups for creating associations
        group_ids = [groups[0].id, -1]  # first is valid, second is invalid

        # verify no preexisting associations
        assert len(user.groups) == 0

        # try to set associations
        with pytest.raises(RequestParameterInvalidException):
            GalaxyRBACAgent(session).set_user_group_and_role_associations(user, group_ids=group_ids)

        # verify no change
        assert len(user.groups) == 0

    def test_invalid_role(self, session, make_user_and_role, make_role):
        """
        State: user exists in database, has no group and only one private role association.
        action: try to add several associations, last one having an invalid role id.
        expect: no associations are added, appropriate error is raised.
        """
        user, private_role = make_user_and_role()
        roles = [make_role() for _ in range(5)]

        # roles for creating associations
        role_ids = [roles[0].id, -1]  # first is valid, second is invalid

        # verify no preexisting associations
        assert len(user.roles) == 1  # one is the private role association

        # try to set associations
        with pytest.raises(RequestParameterInvalidException):
            GalaxyRBACAgent(session).set_user_group_and_role_associations(user, role_ids=role_ids)

        # verify no change
        assert len(user.roles) == 1  # one is the private role association

    def test_duplicate_group(
        self,
        session,
        make_user_and_role,
        make_role,
        make_group,
        make_user_group_association,
        make_user_role_association,
    ):
        """
        State: user exists in database and has group and role associations.
        Action: try update group and role associations including a duplicate group
        Expect: error raised, no change is made to user groups and user roles.
        """
        user, private_role = make_user_and_role()
        groups = [make_group() for _ in range(5)]
        roles = [make_role() for _ in range(5)]

        # load and verify existing associations
        groups_to_load = [groups[0], groups[2]]
        roles_to_load = [roles[1], roles[3]]
        for group in groups_to_load:
            make_user_group_association(user, group)
        for role in roles_to_load:
            make_user_role_association(user, role)
        verify_user_associations(user, groups_to_load, roles_to_load + [private_role])

        # groups and roles for creating new associations
        new_groups_to_add = groups + [groups[0]]  # include a duplicate group
        group_ids = [g.id for g in new_groups_to_add]

        new_roles_to_add = roles  # NO duplicate roles
        role_ids = [r.id for r in new_roles_to_add]

        # sanity check: ensure we are trying to change existing associations
        assert not have_same_elements(groups_to_load, new_groups_to_add)
        assert not have_same_elements(roles_to_load, new_roles_to_add)

        with pytest.raises(RequestParameterInvalidException):
            GalaxyRBACAgent(session).set_user_group_and_role_associations(user, group_ids=group_ids, role_ids=role_ids)

        # verify associations not updated
        verify_user_associations(user, groups_to_load, roles_to_load + [private_role])

    def test_duplicate_role(
        self,
        session,
        make_user_and_role,
        make_role,
        make_group,
        make_user_group_association,
        make_user_role_association,
    ):
        """
        State: user exists in database and has group and role associations.
        Action: try update group and role associations including a duplicate role
        Expect: error raised, no change is made to user groups and user roles.
        """
        user, private_role = make_user_and_role()
        groups = [make_group() for _ in range(5)]
        roles = [make_role() for _ in range(5)]

        # load and verify existing associations
        groups_to_load = [groups[0], groups[2]]
        roles_to_load = [roles[1], roles[3]]
        for group in groups_to_load:
            make_user_group_association(user, group)
        for role in roles_to_load:
            make_user_role_association(user, role)
        verify_user_associations(user, groups_to_load, roles_to_load + [private_role])

        # groups and roles for creating new associations
        new_groups_to_add = groups  # NO duplicate groups
        group_ids = [g.id for g in new_groups_to_add]

        new_roles_to_add = roles + [roles[0]]  # include a duplicate role
        role_ids = [r.id for r in new_roles_to_add]

        # sanity check: ensure we are trying to change existing associations
        assert not have_same_elements(groups_to_load, new_groups_to_add)
        assert not have_same_elements(roles_to_load, new_roles_to_add)

        with pytest.raises(RequestParameterInvalidException):
            GalaxyRBACAgent(session).set_user_group_and_role_associations(user, group_ids=group_ids, role_ids=role_ids)

        # verify associations not updated
        verify_user_associations(user, groups_to_load, roles_to_load + [private_role])


class TestSetRoleUserAndGroupAssociations:
    """
    Note: a user should always have a private role which is not affected
    by modifying a user's group associations or role associations.
    """

    def test_add_associations_to_existing_role(self, session, make_user_and_role, make_role, make_group):
        """
        State: role exists in database, has no group and no user associations.
        Action: add new associations.
        """
        role = make_role()
        users = [make_user_and_role()[0] for _ in range(5)]
        groups = [make_group() for _ in range(5)]

        # users and groups for creating associations
        users_to_add = [users[0], users[2], users[4]]
        user_ids = [u.id for u in users_to_add]
        groups_to_add = [groups[0], groups[2], groups[4]]
        group_ids = [g.id for g in groups_to_add]

        # verify preexisting associations
        verify_role_associations(role, [], [])

        # set associations
        GalaxyRBACAgent(session).set_role_user_and_group_associations(role, user_ids=user_ids, group_ids=group_ids)

        # verify new associations
        verify_role_associations(role, users_to_add, groups_to_add)

    def test_add_associations_to_new_role(self, session, make_user_and_role, make_group):
        """
        State: user does NOT exist in database, has no group and role associations.
        Action: add new associations.
        """
        role = Role()
        session.add(role)
        assert role.id is None  # role does not exist in database
        users = [make_user_and_role()[0] for _ in range(5)]  # type: ignore[unreachable]
        groups = [make_group() for _ in range(5)]

        # users and groups for creating associations
        users_to_add = [users[0], users[2], users[4]]
        user_ids = [u.id for u in users_to_add]
        groups_to_add = [groups[0], groups[2], groups[4]]
        group_ids = [g.id for g in groups_to_add]

        # set associations
        GalaxyRBACAgent(session).set_role_user_and_group_associations(role, user_ids=user_ids, group_ids=group_ids)

        # verify new associations
        verify_role_associations(role, users_to_add, groups_to_add)

    def test_update_associations(
        self,
        session,
        make_user_and_role,
        make_role,
        make_group,
        make_user_role_association,
        make_group_role_association,
    ):
        """
        State: role exists in database AND has user and group associations.
        Action: update associations (add some/drop some).
        Expect: old associations are REPLACED by new associations.
        """
        role = make_role()
        users = [make_user_and_role()[0] for _ in range(5)]
        groups = [make_group() for _ in range(5)]

        # load and verify existing associations
        users_to_load = [users[1], users[3]]
        groups_to_load = [groups[0], groups[2]]
        for user in users_to_load:
            make_user_role_association(user, role)
        for group in groups_to_load:
            make_group_role_association(group, role)
        verify_role_associations(role, users_to_load, groups_to_load)

        # users and groups for creating new associations
        new_users_to_add = [users[0], users[2], users[4]]
        user_ids = [u.id for u in new_users_to_add]
        new_groups_to_add = [groups[0], groups[2], groups[4]]
        group_ids = [g.id for g in new_groups_to_add]

        # sanity check: ensure we are trying to change existing associations
        assert not have_same_elements(users_to_load, new_users_to_add)
        assert not have_same_elements(groups_to_load, new_groups_to_add)

        # set associations
        GalaxyRBACAgent(session).set_role_user_and_group_associations(role, user_ids=user_ids, group_ids=group_ids)
        # verify new associations
        verify_role_associations(role, new_users_to_add, new_groups_to_add)

    def test_drop_associations(
        self,
        session,
        make_user_and_role,
        make_role,
        make_group,
        make_group_role_association,
        make_user_role_association,
    ):
        """
        State: role exists in database AND has user and group associations.
        Action: drop all associations.
        """
        role = make_role()
        users = [make_user_and_role()[0] for _ in range(5)]
        groups = [make_group() for _ in range(5)]

        # load and verify existing associations
        users_to_load = [users[1], users[3]]
        groups_to_load = [groups[0], groups[2]]
        for user in users_to_load:
            make_user_role_association(user, role)
        for group in groups_to_load:
            make_group_role_association(group, role)
        verify_role_associations(role, users_to_load, groups_to_load)

        # drop associations
        GalaxyRBACAgent(session).set_role_user_and_group_associations(role, user_ids=[], group_ids=[])

        # verify associations dropped
        verify_role_associations(role, [], [])

    def test_invalid_user(self, session, make_role, make_user_and_role):
        """
        State: role exists in database, has no user and group eassociations.
        action: try to add several associations, last one having an invalid user id.
        expect: no associations are added, appropriate error is raised.
        """
        role = make_role()
        users = [make_user_and_role()[0] for _ in range(5)]

        # users for creating associations
        user_ids = [users[0].id, -1]  # first is valid, second is invalid

        # verify no preexisting associations
        assert len(role.users) == 0

        # try to set associations
        with pytest.raises(RequestParameterInvalidException):
            GalaxyRBACAgent(session).set_role_user_and_group_associations(role, user_ids=user_ids)

        # verify no change
        assert len(role.users) == 0

    def test_invalid_group(self, session, make_role, make_group):
        """
        State: role exists in database, has no user and group eassociations.
        Action: try to add several associations, last one having an invalid group id.
        Expect: no associations are added, appropriate error is raised.
        """
        role = make_role()
        groups = [make_group() for _ in range(5)]

        # groups for creating associations
        group_ids = [groups[0].id, -1]  # first is valid, second is invalid

        # verify no preexisting associations
        assert len(role.groups) == 0

        # try to set associations
        with pytest.raises(RequestParameterInvalidException):
            GalaxyRBACAgent(session).set_role_user_and_group_associations(role, group_ids=group_ids)

        # verify no change
        assert len(role.groups) == 0

    def test_duplicate_user(
        self,
        session,
        make_user_and_role,
        make_role,
        make_group,
        make_group_role_association,
        make_user_role_association,
    ):
        """
        State: role exists in database and has group and user associations.
        Action: try update group and user associations including a duplicate user
        Expect: error raised, no change is made to role groups and role users.
        """
        role = make_role()
        users = [make_user_and_role()[0] for _ in range(5)]
        groups = [make_group() for _ in range(5)]

        # load and verify existing associations
        users_to_load = [users[1], users[3]]
        groups_to_load = [groups[0], groups[2]]
        for user in users_to_load:
            make_user_role_association(user, role)
        for group in groups_to_load:
            make_group_role_association(group, role)

        verify_role_associations(role, users_to_load, groups_to_load)

        # users and groups for creating new associations
        new_users_to_add = users + [users[0]]  # include a duplicate user
        user_ids = [u.id for u in new_users_to_add]

        new_groups_to_add = groups  # NO duplicate groups
        group_ids = [g.id for g in new_groups_to_add]

        # sanity check: ensure we are trying to change existing associations
        assert not have_same_elements(users_to_load, new_users_to_add)
        assert not have_same_elements(groups_to_load, new_groups_to_add)

        with pytest.raises(RequestParameterInvalidException):
            GalaxyRBACAgent(session).set_role_user_and_group_associations(role, user_ids=user_ids, group_ids=group_ids)

        # verify associations not updated
        verify_role_associations(role, users_to_load, groups_to_load)

    def test_duplicate_group(
        self,
        session,
        make_user_and_role,
        make_role,
        make_group,
        make_group_role_association,
        make_user_role_association,
    ):
        """
        State: role exists in database and has group and user associations.
        Action: try update group and user associations including a duplicate group
        Expect: error raised, no change is made to role groups and role users.
        """
        role = make_role()
        users = [make_user_and_role()[0] for _ in range(5)]
        groups = [make_group() for _ in range(5)]

        # load and verify existing associations
        users_to_load = [users[1], users[3]]
        groups_to_load = [groups[0], groups[2]]
        for user in users_to_load:
            make_user_role_association(user, role)
        for group in groups_to_load:
            make_group_role_association(group, role)

        verify_role_associations(role, users_to_load, groups_to_load)

        # users and groups for creating new associations
        new_users_to_add = users  # NO duplicate users
        user_ids = [u.id for u in new_users_to_add]

        new_groups_to_add = groups + [groups[0]]  # include a duplicate group
        group_ids = [g.id for g in new_groups_to_add]

        # sanity check: ensure we are trying to change existing associations
        assert not have_same_elements(users_to_load, new_users_to_add)
        assert not have_same_elements(groups_to_load, new_groups_to_add)

        with pytest.raises(RequestParameterInvalidException):
            GalaxyRBACAgent(session).set_role_user_and_group_associations(role, user_ids=user_ids, group_ids=group_ids)

        # verify associations not updated
        verify_role_associations(role, users_to_load, groups_to_load)

    def test_delete_default_user_permissions_and_default_history_permissions(
        self,
        session,
        make_role,
        make_user_and_role,
        make_user_role_association,
        make_default_user_permissions,
        make_default_history_permissions,
        make_history,
    ):
        """
        When setting role users, we check check previously associated users to:
        - delete DefaultUserPermissions for users that are being removed from this role;
        - delete DefaultHistoryPermissions for histories associated with users that are being removed from this role.
        """
        role = make_role()
        users = [make_user_and_role()[0] for _ in range(5)]
        # load and verify existing associations
        user1, user2 = users[0], users[1]
        users_to_load = [user1, user2]
        for user in users_to_load:
            make_user_role_association(user, role)
        verify_role_associations(role, users_to_load, [])

        # users and groups for creating new associations
        new_users_to_add = [users[1], users[2]]  # REMOVE users[0], LEAVE users[1], ADD users[2]
        user_ids = [u.id for u in new_users_to_add]
        # sanity check: ensure we are trying to change existing associations
        assert not have_same_elements(users_to_load, new_users_to_add)

        # load default user permissions
        dup1 = make_default_user_permissions(user=user1, role=role)
        dup2 = make_default_user_permissions(user=user2, role=role)
        assert have_same_elements(user1.default_permissions, [dup1])
        assert have_same_elements(user2.default_permissions, [dup2])

        # load and verify default history permissions for users associated with this role
        history1, history2 = make_history(user=user1), make_history(user=user1)  # 2 histories for user 1
        history3 = make_history(user=user2)  # 1 history for user 2
        dhp1 = make_default_history_permissions(history=history1, role=role)
        dhp2 = make_default_history_permissions(history=history2, role=role)
        dhp3 = make_default_history_permissions(history=history3, role=role)
        assert have_same_elements(history1.default_permissions, [dhp1])
        assert have_same_elements(history2.default_permissions, [dhp2])
        assert have_same_elements(history3.default_permissions, [dhp3])

        # now update role users
        GalaxyRBACAgent(session).set_role_user_and_group_associations(role, user_ids=user_ids)

        # verify user role associations
        verify_role_associations(role, new_users_to_add, [])

        # verify default user permissions
        assert have_same_elements(user1.default_permissions, [])  # user1 was removed from role
        assert have_same_elements(user2.default_permissions, [dup2])  # user2 was NOT removed from role

        # verify default history permissions
        assert have_same_elements(history1.default_permissions, [])
        assert have_same_elements(history2.default_permissions, [])
        assert have_same_elements(history3.default_permissions, [dhp3])


def verify_group_associations(group, expected_users, expected_roles):
    new_group_users = [assoc.user for assoc in group.users]
    new_group_roles = [assoc.role for assoc in group.roles]
    assert have_same_elements(new_group_users, expected_users)
    assert have_same_elements(new_group_roles, expected_roles)


def verify_user_associations(user, expected_groups, expected_roles):
    new_user_groups = [assoc.group for assoc in user.groups]
    new_user_roles = [assoc.role for assoc in user.roles]
    assert have_same_elements(new_user_groups, expected_groups)
    assert have_same_elements(new_user_roles, expected_roles)


def verify_role_associations(role, expected_users, expected_groups):
    new_role_users = [assoc.user for assoc in role.users]
    new_role_groups = [assoc.group for assoc in role.groups]
    assert have_same_elements(new_role_users, expected_users)
    assert have_same_elements(new_role_groups, expected_groups)
