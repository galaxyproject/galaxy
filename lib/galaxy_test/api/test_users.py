from galaxy_test.api._framework import ApiTestCase
from galaxy_test.base.api_asserts import assert_object_id_error
from galaxy_test.base.decorators import (
    requires_admin,
    requires_new_history,
    requires_new_user,
)
from galaxy_test.base.populators import (
    DatasetPopulator,
    PRIVATE_ROLE_TYPE,
    skip_without_tool,
)

TEST_USER_EMAIL = "user_for_users_index_test@bx.psu.edu"
TEST_USER_EMAIL_INDEX_DELETED = "user_for_users_index_deleted_test@bx.psu.edu"
TEST_USER_EMAIL_DELETE = "user_for_delete_test@bx.psu.edu"
TEST_USER_EMAIL_DELETE_CANCEL_JOBS = "user_for_delete_cancel_jobs_test@bx.psu.edu"
TEST_USER_EMAIL_PURGE = "user_for_purge_test@bx.psu.edu"
TEST_USER_EMAIL_UNDELETE = "user_for_undelete_test@bx.psu.edu"
TEST_USER_EMAIL_SHOW = "user_for_show_test@bx.psu.edu"


class TestUsersApi(ApiTestCase):

    @requires_admin
    @requires_new_user
    def test_index(self):
        user = self._setup_user(TEST_USER_EMAIL_INDEX_DELETED)
        all_users_response = self._get("users", admin=True)
        self._assert_status_code_is(all_users_response, 200)
        all_users = all_users_response.json()
        # New user is in list
        assert len([u for u in all_users if u["email"] == TEST_USER_EMAIL_INDEX_DELETED]) == 1
        # Request made from admin user, so should at least self and this
        # new user.
        assert len(all_users) > 1
        # index of deleted users
        self._delete(f"users/{user['id']}", admin=True)
        all_deleted_users_response_1 = self._get("users/deleted", admin=True)
        self._assert_status_code_is(all_deleted_users_response_1, 200)
        payload = {"deleted": "True"}
        all_deleted_users_response_2 = self._get("users", data=payload, admin=True)
        self._assert_status_code_is(all_deleted_users_response_2, 200)
        # user is in list of deleted users
        all_deleted_users = all_deleted_users_response_1.json()
        assert len([u for u in all_deleted_users if u["email"] == TEST_USER_EMAIL_INDEX_DELETED]) == 1
        all_deleted_users = all_deleted_users_response_2.json()
        assert len([u for u in all_deleted_users if u["email"] == TEST_USER_EMAIL_INDEX_DELETED]) == 1

    @requires_new_user
    def test_index_only_self_for_nonadmins(self):
        self._setup_user(TEST_USER_EMAIL)
        with self._different_user():
            all_users_response = self._get("users")
            # Non admin users can only see themselves
            assert len(all_users_response.json()) == 1

    @requires_new_user
    def test_show(self):
        user = self._setup_user(TEST_USER_EMAIL)
        with self._different_user(email=TEST_USER_EMAIL):
            show_response = self.__show(user)
            self._assert_status_code_is(show_response, 200)
            self.__assert_matches_user(user, show_response.json())

    @requires_new_user
    def test_update(self):
        payload = {"username": "linnaeus"}
        user = self._setup_user(TEST_USER_EMAIL)
        not_the_user = self._setup_user("email@example.com")
        with self._different_user(email=TEST_USER_EMAIL):
            # working
            update_response = self.__update(user, data=payload)
            self._assert_status_code_is(update_response, 200)
            update_json = update_response.json()
            assert update_json["username"] == payload["username"]

            # too short
            update_response = self.__update(user, data={"username": ""})
            self._assert_status_code_is(update_response, 400)

            # not them
            update_response = self.__update(not_the_user, data=payload)
            self._assert_status_code_is(update_response, 400)

            # non-existent
            no_user_id = "5d7db0757a2eb7ef"
            update_url = self._api_url(f"users/{no_user_id}")
            update_response = self._put(update_url, data=payload, json=True)
            assert_object_id_error(update_response)

    @requires_admin
    @requires_new_user
    def test_admin_update(self):
        payload = {"username": "flexo"}
        user = self._setup_user(TEST_USER_EMAIL)
        update_url = self._api_url(f"users/{user['id']}")
        update_response = self._put(update_url, data=payload, admin=True, json=True)
        self._assert_status_code_is(update_response, 200)
        update_json = update_response.json()
        assert update_json["username"] == payload["username"]

    @requires_admin
    @requires_new_user
    def test_delete_user(self):
        user = self._setup_user(TEST_USER_EMAIL_DELETE)
        self._delete(f"users/{user['id']}", admin=True)
        updated_user = self._get(f"users/deleted/{user['id']}", admin=True).json()
        assert updated_user["deleted"] is True, updated_user

    @requires_admin
    @requires_new_user
    def test_purge_user(self):
        """Delete user and then purge them."""
        user = self._setup_user(TEST_USER_EMAIL_PURGE)
        response = self._delete(f"users/{user['id']}", admin=True)
        self._assert_status_code_is_ok(response)
        params = dict(purge="True")
        response = self._delete(f"users/{user['id']}", params=params, admin=True, json=True)
        self._assert_status_code_is_ok(response)
        params = {"deleted": "True"}
        purged_user = self._get(f"users/{user['id']}", params, admin=True).json()
        assert purged_user["deleted"] is True, purged_user
        assert purged_user["purged"] is True, purged_user

    @requires_admin
    @requires_new_user
    def test_undelete_user(self):
        """Delete user and then undelete them."""
        user = self._setup_user(TEST_USER_EMAIL_UNDELETE)
        self._delete(f"users/{user['id']}", admin=True)
        payload = {"deleted": "True"}
        deleted_user = self._get(f"users/{user['id']}", payload, admin=True).json()
        assert deleted_user["deleted"] is True, deleted_user
        self._post(f"users/deleted/{user['id']}/undelete", admin=True)
        undeleted_user = self._get(f"users/{user['id']}", admin=True).json()
        assert undeleted_user["deleted"] is False, undeleted_user

    @requires_admin
    @requires_new_user
    @requires_new_history
    @skip_without_tool("cat_data_and_sleep")
    def test_delete_user_cancel_all_jobs(self):
        dataset_populator = DatasetPopulator(self.galaxy_interactor)
        with self._different_user(TEST_USER_EMAIL_DELETE_CANCEL_JOBS):
            user_id = self._get_current_user_id()
            history_id = dataset_populator.new_history()
            hda_id = dataset_populator.new_dataset(history_id)["id"]

            inputs = {
                "input1": {"src": "hda", "id": hda_id},
                "sleep_time": 6000,
            }
            run_response = dataset_populator.run_tool_raw(
                "cat_data_and_sleep",
                inputs,
                history_id,
            )
            self._assert_status_code_is_ok(run_response)

            job_id = run_response.json()["jobs"][0]["id"]

            # Wait a bit for the job to be ready
            expected_job_states = ["new", "queued", "running"]
            dataset_populator.wait_for_job(job_id, ok_states=expected_job_states)

            # Get the job state
            job_response = self._get(f"jobs/{job_id}").json()
            assert job_response["state"] in expected_job_states, job_response

            # Delete user will cancel all jobs
            self._delete(f"users/{user_id}", admin=True)

            # Get the job state again (this time as admin), it should be deleting or deleted
            job_response = self._get(f"jobs/{job_id}", admin=True).json()
            assert job_response["state"] in ["deleting", "deleted"], job_response

    @requires_new_user
    def test_information(self):
        user = self._setup_user(TEST_USER_EMAIL)
        url = self.__url("information/inputs", user)
        response = self._get(url).json()
        assert response["username"] == user["username"]
        assert response["email"] == TEST_USER_EMAIL
        payload = {"username": "newname", "email": "new@email.email"}
        self._put(url, data=payload, json=True)
        response = self._get(url).json()
        assert response["username"] == "newname"
        assert response["email"] == "new@email.email"
        payload = {"username": user["username"], "email": TEST_USER_EMAIL}
        self._put(url, data=payload, json=True)
        response = self._get(url).json()
        assert response["username"] == user["username"]
        assert response["email"] == TEST_USER_EMAIL
        self._put(url, data={"address_0|desc": "_desc"}, json=True)
        response = self._get(url).json()
        assert len(response["addresses"]) == 1
        assert response["addresses"][0]["desc"] == "_desc"

    @requires_new_user
    def test_manage_api_key(self):
        with self._different_user("manage-api-key-test@user.com"):
            user_id = self._get_current_user_id()
            # Initially we have an API key because it is bootstrapped for tests
            response = self._get(f"users/{user_id}/api_key")
            user_api_key = response.json()
            assert user_api_key
            # Test detailed endpoint
            response = self._get(f"users/{user_id}/api_key/detailed")
            api_key = response.json()
            assert api_key["key"] == user_api_key
            # Delete user API key
            response = self._delete(f"users/{user_id}/api_key")
            self._assert_status_code_is(response, 204)
            # No API key anymore, so the detailed request returns no content 204 with admin key
            response = self._get(f"users/{user_id}/api_key/detailed", admin=True)
            self._assert_status_code_is(response, 204)
            # No API key anymore, so the detailed request returns unauthorized 401 with user key
            response = self._get(f"users/{user_id}/api_key/detailed")
            self._assert_status_code_is(response, 401)
            # create new as admin
            response = self._post(f"users/{user_id}/api_key", admin=True)
            self._assert_status_code_is_ok(response)
            new_api_key = response.json()
            assert new_api_key
            assert new_api_key != user_api_key

    @requires_new_user
    def test_only_admin_can_manage_other_users_api_key(self):
        with self._different_user():
            other_user_id = self._get_current_user_id()
        current_user_id = self._get_current_user_id()
        # Users cannot access other users API keys
        assert current_user_id != other_user_id
        response = self._get(f"users/{other_user_id}/api_key")
        self._assert_status_code_is(response, 403)
        response = self._post(f"users/{other_user_id}/api_key")
        self._assert_status_code_is(response, 403)
        response = self._delete(f"users/{other_user_id}/api_key")
        self._assert_status_code_is(response, 403)

        # Admins can access other users API keys
        response = self._get(f"users/{other_user_id}/api_key", admin=True)
        self._assert_status_code_is_ok(response)
        response = self._post(f"users/{other_user_id}/api_key", admin=True)
        self._assert_status_code_is_ok(response)
        response = self._delete(f"users/{other_user_id}/api_key", admin=True)
        self._assert_status_code_is_ok(response)

    @requires_admin
    @requires_new_user
    @skip_without_tool("cat1")
    def test_favorites(self):
        user = self._setup_user(TEST_USER_EMAIL)
        # adding a tool to favorites
        url = self._api_url(f"users/{user['id']}/favorites/tools")
        put_response = self._put(url, data={"object_id": "cat1"}, admin=True, json=True)
        self._assert_status_code_is_ok(put_response)
        assert put_response.json()["tools"][0] == "cat1"
        # not implemented for workflows yet
        url = self._api_url(f"users/{user['id']}/favorites/workflows")
        put_response = self._put(url, data={"object_id": "14ds68f4sda68gf46dsag4"}, admin=True, json=True)
        self._assert_status_code_is(put_response, 400)
        # delete existing tool favorite
        url = self._api_url(f"users/{user['id']}/favorites/tools/cat1")
        delete_response = self._delete(url, admin=True)
        self._assert_status_code_is_ok(delete_response)
        assert delete_response.json()["tools"] == []
        # delete non-existing tool favorite
        url = self._api_url(f"users/{user['id']}/favorites/tools/madeuptoolthatdoes/not/exist/in/favs")
        delete_response = self._delete(url, admin=True)
        self._assert_status_code_is(delete_response, 404)
        # delete non existing workflow favorite
        url = self._api_url(f"users/{user['id']}/favorites/workflows/1as5das5das56d465")
        delete_response = self._delete(url, admin=True)
        self._assert_status_code_is(delete_response, 400)

    @skip_without_tool("cat1")
    def test_search_favorites(self):
        user, user_key = self._setup_user_get_key(TEST_USER_EMAIL)
        url = self._api_url(f"users/{user['id']}/favorites/tools", params=dict(key=user_key))
        fav_response = self._put(url, data={"object_id": "cat1"}, json=True)
        self._assert_status_code_is_ok(fav_response)
        assert "cat1" in fav_response.json()["tools"]
        url = self._api_url("tools", params=dict(q="#favs", key=user_key))
        search_response = self._get(url).json()
        assert "cat1" in search_response

    @requires_new_user
    def test_set_theme(self):
        user = self._setup_user(TEST_USER_EMAIL)
        with self._different_user(email=TEST_USER_EMAIL):
            url = self._api_url(f"users/{user['id']}/theme/test_theme")
            theme_response = self._put(url)
            self._assert_status_code_is_ok(theme_response)
            url = self._api_url("users/current")
            updated_theme = self._get(url).json()["preferences"]["theme"]
            assert updated_theme == "test_theme"

    @requires_admin
    @requires_new_user
    def test_show_delete(self):
        user = self._setup_user(TEST_USER_EMAIL_SHOW)
        url = self._api_url(f"users/{user['id']}")
        response_1 = self._get(url, admin=True).json()
        self._delete(f"users/{user['id']}", admin=True)

        # Both request should return the same user
        response_2 = self._get(f"users/deleted/{user['id']}", admin=True).json()
        payload = {"deleted": "True"}
        response_3 = self._get(f"users/{user['id']}", payload, admin=True).json()
        assert response_1["id"] == response_2["id"] == response_3["id"]
        assert response_2 == response_3

    def test_show_current(self):
        user_id = self._get_current_user_id()
        url = self._api_url(f"users/{user_id}")
        specified_user = self._get(url).json()
        url = self._api_url("users/current")
        current_user = self._get(url).json()
        assert specified_user == current_user

    def __url(self, action, user):
        return self._api_url(f"users/{user['id']}/{action}", params=dict(key=self.master_api_key))

    def __show(self, user):
        return self._get(f"users/{user['id']}")

    def __update(self, user, data):
        update_url = self._api_url(f"users/{user['id']}")
        return self._put(update_url, data=data, json=True)

    def __assert_matches_user(self, userA, userB):
        self._assert_has_keys(userB, "id", "username", "total_disk_usage")
        assert userA["id"] == userB["id"]
        assert userA["username"] == userB["username"]

    def _get_current_user_id(self):
        users_response = self._get("users")
        users = users_response.json()
        assert len(users) == 1
        return users[0]["id"]

    def test_manage_beacon_settings(self):
        user_id = self._get_current_user_id()

        # Assert that beacon sharing is initially disabled
        response = self._get(f"users/{user_id}/beacon")
        user_beacon_settings = response.json()
        assert not user_beacon_settings["enabled"]

        # Check if post request is successful
        response = self._post(f"users/{user_id}/beacon", data={"enabled": True}, json=True)
        user_beacon_settings = response.json()
        assert user_beacon_settings["enabled"]

        # Check if the setting has been persisted
        response = self._get(f"users/{user_id}/beacon")
        user_beacon_settings = response.json()
        assert user_beacon_settings["enabled"]

    @requires_admin
    @requires_new_user
    def test_user_roles(self):
        user = self._setup_user(TEST_USER_EMAIL)
        response = self._get(f"users/{user['id']}/roles", admin=True)
        user_roles = response.json()
        assert len(user_roles) == 1
        assert user_roles[0]["type"] == PRIVATE_ROLE_TYPE
