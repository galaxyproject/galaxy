from galaxy_test.base.decorators import requires_admin
from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class TestAdminRoleAndUserForms(SeleniumTestCase):
    run_as_admin = True

    @selenium_test
    @requires_admin
    def test_edit_role(self):
        kept_email = self._get_random_email("kept")
        removed_email = self._get_random_email("removed")
        added_email = self._get_random_email("added")
        user_ids = {
            email: self.galaxy_interactor.ensure_user_with_email(email)["id"]
            for email in (kept_email, removed_email, added_email)
        }
        group_name = self.dataset_populator.create_group()["name"]
        role_response = self._post(
            "roles",
            data={
                "name": self._get_random_name(prefix="editedrole"),
                "description": "role edited through the admin form",
                "user_ids": [user_ids[kept_email], user_ids[removed_email]],
            },
            admin=True,
            json=True,
        )
        role_response.raise_for_status()
        role_id = role_response.json()["id"]

        self.admin_login()
        self.get(f"admin/form/edit_role?id={role_id}")
        role_component = self.components.admin.role
        role_component.form.wait_for_visible()
        role_component.selected_user(email=kept_email).wait_for_visible()
        role_component.remove_selected_user(email=removed_email).wait_for_and_click()
        role_component.selected_user(email=removed_email).wait_for_absent()
        role_component.users.wait_for_and_click()
        role_component.users_input.wait_for_and_send_keys(added_email)
        role_component.user_option(email=added_email).wait_for_and_click()
        role_component.groups.wait_for_and_click()
        role_component.groups_input.wait_for_and_send_keys(group_name)
        role_component.group_option(name=group_name).wait_for_and_click()
        self.screenshot("admin_role_edit")
        role_component.submit.wait_for_and_click()
        self.components.admin.roles_grid.wait_for_visible()

        role_users = self._get(f"roles/{role_id}/users", admin=True).json()
        assert sorted(user["email"] for user in role_users) == sorted([kept_email, added_email])
        role_groups = self._get(f"roles/{role_id}/groups", admin=True).json()
        assert [group["name"] for group in role_groups] == [group_name]

    @selenium_test
    @requires_admin
    def test_manage_user_roles_and_groups(self):
        email = self._get_random_email("rolesandgroups")
        user_id = self.galaxy_interactor.ensure_user_with_email(email)["id"]
        kept_role = self.dataset_populator.create_role([user_id])
        removed_role = self.dataset_populator.create_role([user_id])
        added_role = self.dataset_populator.create_role([])
        group_name = self.dataset_populator.create_group()["name"]

        self.admin_login()
        self.get(f"admin/form/manage_roles_and_groups_for_user?id={user_id}")
        form_component = self.components.admin.user_roles_groups
        form_component.form.wait_for_visible()
        form_component.selected_role(name=kept_role["name"]).wait_for_visible()
        form_component.remove_selected_role(name=removed_role["name"]).wait_for_and_click()
        form_component.selected_role(name=removed_role["name"]).wait_for_absent()
        form_component.roles.wait_for_and_click()
        form_component.roles_input.wait_for_and_send_keys(added_role["name"])
        form_component.role_option(name=added_role["name"]).wait_for_and_click()
        form_component.groups.wait_for_and_click()
        form_component.groups_input.wait_for_and_send_keys(group_name)
        form_component.group_option(name=group_name).wait_for_and_click()
        self.screenshot("admin_user_roles_and_groups")
        form_component.submit.wait_for_and_click()
        self.components.admin.users_grid.wait_for_visible()

        user_roles = self._get(f"users/{user_id}/roles", admin=True).json()
        non_private_role_ids = sorted(role["id"] for role in user_roles if role["type"] != "private")
        assert non_private_role_ids == sorted([kept_role["id"], added_role["id"]])
        assert [role["type"] for role in user_roles].count("private") == 1
        user_groups = self._get(f"users/{user_id}/groups", admin=True).json()
        assert [group["name"] for group in user_groups] == [group_name]
