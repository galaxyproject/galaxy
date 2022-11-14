from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util


class QuotaIntegrationTestCase(integration_util.IntegrationTestCase):
    require_admin_user = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_quotas"] = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_create(self):
        self._create_quota_with_name("test-create-quota")

    def test_index(self):
        self._create_quota_with_name("test-index-quota")
        index_response = self._get("quotas")
        index_response.raise_for_status()
        json_response = index_response.json()
        assert len(json_response) > 0

    def test_index_deleted(self):
        quota = self._create_quota_with_name("test-index-deleted-quota")
        quota_id = quota["id"]
        delete_response = self._delete(f"quotas/{quota_id}")
        delete_response.raise_for_status()
        index_response = self._get("quotas/deleted")
        index_response.raise_for_status()
        json_response = index_response.json()
        assert len(json_response) > 0

    def test_show(self):
        quota_name = "test-show-quota"
        quota = self._create_quota_with_name(quota_name)
        quota_id = quota["id"]
        show_response = self._get(f"quotas/{quota_id}")
        show_response.raise_for_status()
        json_response = show_response.json()
        assert json_response["name"] == quota["name"]

    def test_show_deleted(self):
        quota_name = "test-show-deleted-quota"
        quota = self._create_quota_with_name(quota_name)
        quota_id = quota["id"]
        delete_response = self._delete(f"quotas/{quota_id}")
        delete_response.raise_for_status()
        show_response = self._get(f"quotas/deleted/{quota_id}")
        show_response.raise_for_status()
        json_response = show_response.json()
        assert json_response["name"] == quota["name"]

    def test_update(self):
        quota_name = "test-update-quota"
        quota = self._create_quota_with_name(quota_name)
        quota_id = quota["id"]

        new_quota_name = "updated-quota-name"
        update_payload = {
            "name": new_quota_name,
        }
        put_response = self._put(f"quotas/{quota_id}", data=update_payload, json=True)
        put_response.raise_for_status()
        assert "has been renamed to" in put_response.text

        show_response = self._get(f"quotas/{quota_id}")
        show_response.raise_for_status()
        json_response = show_response.json()
        assert json_response["name"] == new_quota_name

    def test_delete(self):
        quota_name = "test-delete-quota"
        quota = self._create_quota_with_name(quota_name)
        quota_id = quota["id"]
        delete_response = self._delete(f"quotas/{quota_id}")
        delete_response.raise_for_status()
        self._assert_quota_is_deleted(quota_id)

    def test_delete_and_purge(self):
        quota_name = "test-delete-purge-quota"
        quota = self._create_quota_with_name(quota_name)
        quota_id = quota["id"]
        delete_response = self._delete_and_purge(quota_id)
        delete_response.raise_for_status()
        self._assert_quota_is_deleted(quota_id)

    def test_delete_and_purge_with_user(self):
        user_email = "test@galaxy.test"
        self.galaxy_interactor.ensure_user_with_email(user_email)

        quota_name = "test-delete-purge-quota-user"
        payload = self._build_quota_payload_with_name(quota_name)
        payload["in_users"].append(user_email)
        create_response = self._post("quotas", data=payload, json=True)
        create_response.raise_for_status()
        quota = create_response.json()
        quota_id = quota["id"]

        show_response = self._get(f"quotas/{quota_id}")
        show_response.raise_for_status()
        json_response = show_response.json()
        assert user_email in str(json_response["users"])

        delete_response = self._delete_and_purge(quota_id)
        delete_response.raise_for_status()
        show_response = self._get(f"quotas/deleted/{quota_id}")
        show_response.raise_for_status()
        json_response = show_response.json()
        assert user_email not in str(json_response["users"])

    def test_undelete(self):
        quota_name = "test-undelete-quota"
        quota = self._create_quota_with_name(quota_name)
        quota_id = quota["id"]
        delete_response = self._delete(f"quotas/{quota_id}")
        delete_response.raise_for_status()
        self._assert_quota_is_deleted(quota_id)

        undelete_response = self._post(f"quotas/deleted/{quota_id}/undelete")
        undelete_response.raise_for_status()

        show_response = self._get(f"quotas/{quota_id}")
        show_response.raise_for_status()

        show_response = self._get(f"quotas/deleted/{quota_id}")
        self._assert_status_code_is(show_response, 400)

    def test_400_when_delete_default(self):
        quota_name = "test-delete-default-quota"
        quota = self._create_quota_with_name(quota_name, is_default=True)
        quota_id = quota["id"]
        delete_response = self._delete(f"quotas/{quota_id}")
        self._assert_status_code_is(delete_response, 400)

    def test_400_when_quota_name_already_exists(self):
        quota_name = "test-duplicated-quota"
        self._create_quota_with_name(quota_name)
        payload = self._build_quota_payload_with_name(quota_name)
        create_response = self._post("quotas", data=payload, json=True)
        self._assert_status_code_is(create_response, 400)

    def test_400_when_show_unknown_quota(self):
        quota_id = "unknown-id"
        show_response = self._get(f"quotas/{quota_id}")
        self._assert_status_code_is(show_response, 400)

    def test_400_when_invalid_amount(self):
        invalid_amount = ""
        quota_name = "invalid-amount-id"
        payload = {
            "name": quota_name,
            "description": f"Quota {quota_name} description",
            "amount": invalid_amount,
            "operation": "=",
            "default": "no",
            "in_users": [],
            "in_groups": [],
        }
        create_response = self._post("quotas", data=payload, json=True)
        self._assert_status_code_is(create_response, 400)

    def _create_quota_with_name(self, quota_name: str, is_default: bool = False):
        payload = self._build_quota_payload_with_name(quota_name, is_default)
        create_response = self._post("quotas", data=payload, json=True)
        create_response.raise_for_status()
        return create_response.json()

    def _build_quota_payload_with_name(self, quota_name: str, is_default: bool = False):
        default = "registered" if is_default else "no"
        return {
            "name": quota_name,
            "description": f"Quota {quota_name} description",
            "amount": "100MB",
            "operation": "=",
            "default": default,
            "in_users": [],
            "in_groups": [],
        }

    def _delete_and_purge(self, quota_id):
        data = {"purge": "true"}
        return self._delete(f"quotas/{quota_id}", data=data, admin=True, json=True)

    def _assert_quota_is_deleted(self, quota_id: str):
        show_response = self._get(f"quotas/deleted/{quota_id}")
        show_response.raise_for_status()
        json_response = show_response.json()
        assert json_response["id"] == quota_id
