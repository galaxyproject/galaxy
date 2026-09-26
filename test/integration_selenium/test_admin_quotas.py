from galaxy_test.base.decorators import requires_admin
from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)


class TestAdminQuotasSeleniumIntegration(SeleniumIntegrationTestCase):
    run_as_admin = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_quotas"] = True

    @selenium_test
    @requires_admin
    def test_manage_quota_users_and_groups(self):
        kept_email = self._get_random_email("kept")
        removed_email = self._get_random_email("removed")
        added_email = self._get_random_email("added")
        for email in (kept_email, removed_email, added_email):
            self.galaxy_interactor.ensure_user_with_email(email)
        group_name = self._get_random_name(prefix="quotagroup")
        group_response = self._post("groups", data={"name": group_name}, admin=True, json=True)
        group_response.raise_for_status()
        quota_response = self._post(
            "quotas",
            data={
                "name": self._get_random_name(prefix="managedquota"),
                "description": "quota with managed users and groups",
                "amount": "10MB",
                "operation": "=",
                "default": "no",
                "in_users": [kept_email, removed_email],
                "in_groups": [],
            },
            admin=True,
            json=True,
        )
        quota_response.raise_for_status()
        quota_id = quota_response.json()["id"]

        self.admin_login()
        self.get(f"admin/form/manage_users_and_groups_for_quota?id={quota_id}")
        quota_component = self.components.admin.quota
        quota_component.form.wait_for_visible()
        quota_component.selected_user(email=kept_email).wait_for_visible()
        quota_component.remove_selected_user(email=removed_email).wait_for_and_click()
        quota_component.selected_user(email=removed_email).wait_for_absent()
        self.quota_form_add_user(added_email)
        self.quota_form_add_group(group_name)
        self.screenshot("admin_quota_manage_users_and_groups")
        quota_component.submit.wait_for_and_click()
        quota_component.items.wait_for_element_count_of_at_least(1)

        show_response = self._get(f"quotas/{quota_id}", admin=True)
        show_response.raise_for_status()
        quota = show_response.json()
        assert sorted(a["user"]["email"] for a in quota["users"]) == sorted([kept_email, added_email])
        assert [a["group"]["name"] for a in quota["groups"]] == [group_name]
