import json

from requests import (
    delete,
    get,
    put
)

from base import api  # noqa: I100,I202
from base.populators import skip_without_tool

TEST_USER_EMAIL = "user_for_users_index_test@bx.psu.edu"


class UsersApiTestCase(api.ApiTestCase):

    def test_index(self):
        self._setup_user(TEST_USER_EMAIL)
        all_users_response = self._get("users", admin=True)
        self._assert_status_code_is(all_users_response, 200)
        all_users = all_users_response.json()
        # New user is in list
        assert len([u for u in all_users if u["email"] == TEST_USER_EMAIL]) == 1
        # Request made from admin user, so should at least self and this
        # new user.
        assert len(all_users) > 1

    def test_index_only_self_for_nonadmins(self):
        self._setup_user(TEST_USER_EMAIL)
        with self._different_user():
            all_users_response = self._get("users")
            # Non admin users can only see themselves
            assert len(all_users_response.json()) == 1

    def test_show(self):
        user = self._setup_user(TEST_USER_EMAIL)
        with self._different_user(email=TEST_USER_EMAIL):
            show_response = self.__show(user)
            self._assert_status_code_is(show_response, 200)
            self.__assert_matches_user(user, show_response.json())

    def test_update(self):
        new_name = 'linnaeus'
        user = self._setup_user(TEST_USER_EMAIL)
        not_the_user = self._setup_user('email@example.com')
        with self._different_user(email=TEST_USER_EMAIL):

            # working
            update_response = self.__update(user, username=new_name)
            self._assert_status_code_is(update_response, 200)
            update_json = update_response.json()
            self.assertEqual(update_json['username'], new_name)

            # too short
            update_response = self.__update(user, username='mu')
            self._assert_status_code_is(update_response, 400)

            # not them
            update_response = self.__update(not_the_user, username=new_name)
            self._assert_status_code_is(update_response, 403)

            # non-existent
            no_user_id = self.security.encode_id(100)
            update_url = self._api_url("users/%s" % (no_user_id), use_key=True)
            update_response = put(update_url, data=json.dumps(dict(username=new_name)))
            self._assert_status_code_is(update_response, 404)

    def test_admin_update(self):
        new_name = 'flexo'
        user = self._setup_user(TEST_USER_EMAIL)
        update_url = self._api_url("users/%s" % (user["id"]), params=dict(key=self.master_api_key))
        update_response = put(update_url, data=json.dumps(dict(username=new_name)))
        self._assert_status_code_is(update_response, 200)
        update_json = update_response.json()
        self.assertEqual(update_json['username'], new_name)

    def test_information(self):
        user = self._setup_user(TEST_USER_EMAIL)
        url = self.__url("information/inputs", user)
        response = get(url).json()
        self.assertEqual(response["username"], user["username"])
        self.assertEqual(response["email"], TEST_USER_EMAIL)
        put(url, data=json.dumps(dict(username="newname", email="new@email.email")))
        response = get(url).json()
        self.assertEqual(response["username"], "newname")
        self.assertEqual(response["email"], "new@email.email")
        put(url, data=json.dumps(dict(username=user["username"], email=TEST_USER_EMAIL)))
        response = get(url).json()
        self.assertEqual(response["username"], user["username"])
        self.assertEqual(response["email"], TEST_USER_EMAIL)
        put(url, data=json.dumps({"address_0|desc" : "_desc"}))
        response = get(url).json()
        self.assertEqual(len(response["addresses"]), 1)
        self.assertEqual(response["addresses"][0]["desc"], "_desc")

    @skip_without_tool("cat1")
    def test_favorites(self):
        user = self._setup_user(TEST_USER_EMAIL)
        # adding a tool to favorites
        url = self._api_url("users/%s/favorites/tools" % user["id"], params=dict(key=self.master_api_key))
        put_response = put(url, data=json.dumps({"object_id" : "cat1"}))
        self._assert_status_code_is_ok(put_response)
        self.assertEqual(put_response.json()["tools"][0], "cat1")
        # not implemented for workflows yet
        url = self._api_url("users/%s/favorites/workflows" % user["id"], params=dict(key=self.master_api_key))
        put_response = put(url, data=json.dumps({"object_id" : "14ds68f4sda68gf46dsag4"}))
        self._assert_status_code_is(put_response, 400)
        # delete existing tool favorite
        url = self._api_url("users/%s/favorites/tools/cat1" % user["id"], params=dict(key=self.master_api_key))
        delete_response = delete(url)
        self._assert_status_code_is_ok(delete_response)
        self.assertEqual(delete_response.json()["tools"], [])
        # delete non-existing tool favorite
        url = self._api_url("users/%s/favorites/tools/madeuptoolthatdoes/not/exist/in/favs" % user["id"], params=dict(key=self.master_api_key))
        delete_response = delete(url)
        self._assert_status_code_is(delete_response, 404)
        # delete non existing workflow favorite
        url = self._api_url("users/%s/favorites/workflows/1as5das5das56d465" % user["id"], params=dict(key=self.master_api_key))
        delete_response = delete(url)
        self._assert_status_code_is(delete_response, 400)

    @skip_without_tool("cat1")
    def test_search_favorites(self):
        user = self._setup_user(TEST_USER_EMAIL)
        user_key = self._setup_user_get_key(TEST_USER_EMAIL)
        url = self._api_url("users/%s/favorites/tools" % user["id"], params=dict(key=user_key))
        fav_response = put(url, data=json.dumps({"object_id" : "cat1"}))
        self._assert_status_code_is_ok(fav_response)
        assert "cat1" in fav_response.json()["tools"]
        url = self._api_url("tools", params=dict(q="#favs", key=user_key))
        search_response = get(url).json()
        assert "cat1" in search_response

    def test_communication(self):
        user = self._setup_user(TEST_USER_EMAIL)
        url = self.__url("communication/inputs", user)
        self.assertEqual(self.__filter(get(url).json(), "enable", "value"), "false")
        put(url, data=json.dumps(dict(enable="true")))
        self.assertEqual(self.__filter(get(url).json(), "enable", "value"), "true")

    def __filter(self, response, name, attr):
        return [r[attr] for r in response["inputs"] if r["name"] == name][0]

    def __url(self, action, user):
        return self._api_url("users/%s/%s" % (user["id"], action), params=dict(key=self.master_api_key))

    def __show(self, user):
        return self._get("users/%s" % (user['id']))

    def __update(self, user, **new_data):
        update_url = self._api_url("users/%s" % (user["id"]), use_key=True)
        return put(update_url, data=new_data)

    def __assert_matches_user(self, userA, userB):
        self._assert_has_keys(userB, "id", "username", "total_disk_usage")
        assert userA["id"] == userB["id"]
        assert userA["username"] == userB["username"]
