import json
import os
from typing import Any

from galaxy.model import User
from galaxy.model.db.user import get_user_by_email
from galaxy_test.driver import integration_util

EXTRA_PREFS_CONF = os.path.join(os.path.dirname(__file__), "user_preferences_extra_conf.yml")


class TestExtraUserPreferences(integration_util.IntegrationTestCase, integration_util.ConfiguresDatabaseVault):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls._configure_database_vault(config)
        config["user_preferences_extra_conf_path"] = EXTRA_PREFS_CONF
        config["allow_user_deletion"] = True

    def test_definition(self):
        with self._different_user("extra-prefs-definition@test.gx"):
            response = self._get("configuration/extra_preferences")
            self._assert_status_code_is(response, 200)
        sections = {section["name"]: section for section in response.json()}
        assert set(sections) == {"vaulttestsection", "non_vault_test_section", "typed_section", "lenient_section"}
        assert [input["name"] for input in sections["lenient_section"]["inputs"]] == ["valid"]
        languages = [input for input in sections["typed_section"]["inputs"] if input["name"] == "languages"][0]
        assert languages["multiple"] is True
        language = [input for input in sections["typed_section"]["inputs"] if input["name"] == "language"][0]
        assert language["type"] == "select"
        assert language["options"] == [["English", "en"], ["Deutsch", "de"]]
        refresh_token = [input for input in sections["vaulttestsection"]["inputs"] if input["name"] == "refresh_token"]
        assert refresh_token[0]["store"] == "vault"
        plain_password = [input for input in sections["typed_section"]["inputs"] if input["name"] == "plain_password"]
        assert plain_password[0]["value"] is None

        with self._different_user(anon=True):
            self._assert_status_code_is(self._get("configuration/extra_preferences"), 403)

    def test_vault_storage(self):
        email = "extra-prefs-vault@test.gx"
        with self._different_user(email):
            response = self._put_prefs(
                {
                    "vaulttestsection": {
                        "client_id": "hello_client_id",
                        "client_secret": "hello_client_secret",
                        "refresh_token": "a_super_secret_value",
                    }
                }
            )
            self._assert_status_code_is(response, 200)
            values = response.json()["vaulttestsection"]
            assert self._get_prefs()["vaulttestsection"] == values

        assert values["client_id"] == "hello_client_id"
        assert values["client_secret"] == {"is_set": True}
        assert values["refresh_token"] == {"is_set": True}
        assert values["access_token"] == {"is_set": False}

        user = self._db_user(email)
        assert user.extra_preferences["vaulttestsection|client_id"] == "hello_client_id"
        assert self._read_vault(user, "vaulttestsection/client_id") is None
        assert self._read_vault(user, "vaulttestsection/client_secret") == "hello_client_secret"
        assert self._read_vault(user, "vaulttestsection/refresh_token") == "a_super_secret_value"
        assert user.extra_preferences["vaulttestsection|client_secret"] is None

    def test_secret_not_in_vault(self):
        email = "extra-prefs-non-vault@test.gx"
        with self._different_user(email):
            self._put_prefs({"non_vault_test_section": {"user": "test_user", "pass": "test_pass"}})
            values = self._get_prefs()["non_vault_test_section"]
        assert values == {"user": "test_user", "pass": {"is_set": True}}

        user = self._db_user(email)
        assert user.extra_preferences["non_vault_test_section|pass"] == "test_pass"
        assert self._read_vault(user, "non_vault_test_section/pass") is None

    def test_omitted_inputs_keep_their_value(self):
        email = "extra-prefs-merge@test.gx"
        with self._different_user(email):
            self._put_prefs(
                {
                    "non_vault_test_section": {"user": "test_user", "pass": "test_pass"},
                    "vaulttestsection": {"refresh_token": "kept_secret"},
                }
            )
            self._put_prefs({"non_vault_test_section": {"user": "a_new_test_user"}})
            self._put_prefs({"vaulttestsection": {"client_id": "a_client_id"}})

        user = self._db_user(email)
        assert user.extra_preferences["non_vault_test_section|user"] == "a_new_test_user"
        assert user.extra_preferences["non_vault_test_section|pass"] == "test_pass"
        assert self._read_vault(user, "vaulttestsection/refresh_token") == "kept_secret"

    def test_null_clears_a_value(self):
        email = "extra-prefs-clear@test.gx"
        with self._different_user(email):
            self._put_prefs({"typed_section": {"note": "a note", "optional_token": "a_token", "vault_count": 3}})
            response = self._put_prefs({"typed_section": {"note": None, "optional_token": None, "vault_count": None}})
            self._assert_status_code_is(response, 200)
        cleared = response.json()["typed_section"]
        assert cleared["note"] is None
        assert cleared["optional_token"] == {"is_set": False}
        assert cleared["vault_count"] is None

        user = self._db_user(email)
        assert "typed_section|note" not in json.loads(user.preferences["extra_user_preferences"])
        assert not self._read_vault(user, "typed_section/optional_token")

    def test_required_input_cannot_be_cleared(self):
        with self._different_user("extra-prefs-required@test.gx"):
            self._put_prefs({"non_vault_test_section": {"user": "test_user"}})
            for empty in ("", None):
                response = self._put_prefs({"non_vault_test_section": {"user": empty}})
                self._assert_status_code_is(response, 400)
            assert self._get_prefs()["non_vault_test_section"]["user"] == "test_user"

    def test_invalid_payload_writes_nothing(self):
        email = "extra-prefs-invalid@test.gx"
        with self._different_user(email):
            invalid: list[tuple[str, dict[str, Any]]] = [
                ("no_such_section", {"x": "y"}),
                ("vaulttestsection", {"no_such_input": "y"}),
                ("typed_section", {"flag": "yes"}),
                ("typed_section", {"language": "fr"}),
                ("typed_section", {"untyped_choice": "three"}),
                ("typed_section", {"note": 5}),
                ("typed_section", {"vault_count": True}),
            ]
            for section, inputs in invalid:
                payload: dict[str, dict[str, Any]] = {"vaulttestsection": {"refresh_token": "must_not_be_written"}}
                payload[section] = payload.get(section, {}) | inputs
                response = self._put_prefs(payload)
                self._assert_status_code_is(response, 400)
            response = self._put_prefs({"typed_section": {"flag": True, "language": "de", "untyped_choice": "two"}})
            self._assert_status_code_is(response, 200)

        user = self._db_user(email)
        assert self._read_vault(user, "vaulttestsection/refresh_token") is None
        assert user.extra_preferences["typed_section|flag"] is True

    def test_typed_values_round_trip(self):
        typed = {"flag": False, "languages": ["de", "en"], "vault_flag": False, "vault_count": 3, "vault_level": 2}
        with self._different_user("extra-prefs-round-trip@test.gx"):
            response = self._put_prefs({"typed_section": typed})
            self._assert_status_code_is(response, 200)
            values = self._get_prefs()["typed_section"]
            assert {name: values[name] for name in typed} == typed
            # everything but the {"is_set": ...} states of sensitive inputs can be sent back as it came
            unchanged = {name: value for name, value in values.items() if not isinstance(value, dict)}
            self._assert_status_code_is(self._put_prefs({"typed_section": unchanged}), 200)
            self._assert_status_code_is(self._put_prefs({"typed_section": {"languages": ["fr"]}}), 400)
            self._assert_status_code_is(self._put_prefs({"typed_section": {"languages": "en"}}), 400)

            user_id = self._get("users/current").json()["id"]
            form = self._get(f"users/{user_id}/information/inputs")
            self._assert_status_code_is(form, 200)

    def test_values_are_read_by_exact_key(self):
        email = "extra-prefs-exact-key@test.gx"
        with self._different_user(email):
            self._get_prefs()
        user = self._db_user(email)
        user.preferences["extra_user_preferences"] = json.dumps(
            {"typed_section|note_suffix": "not the note", "typed_section|flag": "true", "typed_section|note_list": [1]}
        )
        self._app.model.session.commit()
        with self._different_user(email):
            values = self._get_prefs()["typed_section"]
        assert values["note"] is None
        assert values["flag"] is True

    def test_other_users_values_are_forbidden(self):
        owner = self._setup_user("extra-prefs-owner@test.gx")
        with self._different_user("extra-prefs-other@test.gx"):
            self._assert_status_code_is(self._get(f"users/{owner['id']}/extra_preferences"), 403)
            response = self._put(
                f"users/{owner['id']}/extra_preferences", data={"typed_section": {"note": "x"}}, json=True
            )
            self._assert_status_code_is(response, 403)

    def test_legacy_information_inputs(self):
        email = "extra-prefs-legacy@test.gx"
        user = self._setup_user(email)
        legacy_url = f"users/{user['id']}/information/inputs"
        with self._different_user(email):
            response = self._put(
                legacy_url,
                data={
                    "vaulttestsection|client_id": "legacy_client_id",
                    "vaulttestsection|client_secret": "legacy_client_secret",
                    "vaulttestsection|no_such_input": "dropped",
                    "non_vault_test_section|user": "legacy_user",
                    "non_vault_test_section|pass": "legacy_pass",
                },
                json=True,
            )
            self._assert_status_code_is(response, 200)
            form = self._get(legacy_url).json()

            sections = {section["name"]: section for section in form["inputs"] if section.get("type") == "section"}
            vault_inputs = {input["name"]: input for input in sections["vaulttestsection"]["inputs"]}
            assert vault_inputs["client_id"]["value"] == "legacy_client_id"
            for sensitive in ("client_secret", "refresh_token"):
                assert vault_inputs[sensitive]["value"] == "__SECRET_PLACEHOLDER__"
                assert vault_inputs[sensitive]["type"] == "password"

            # the form sends the placeholder back for secrets the user did not edit
            response = self._put(
                legacy_url,
                data={
                    "vaulttestsection|client_secret": "__SECRET_PLACEHOLDER__",
                    "non_vault_test_section|pass": "__SECRET_PLACEHOLDER__",
                },
                json=True,
            )
            self._assert_status_code_is(response, 200)
            assert self._get_prefs()["vaulttestsection"]["client_id"] == "legacy_client_id"

        db_user = self._db_user(email)
        assert self._read_vault(db_user, "vaulttestsection/client_secret") == "legacy_client_secret"
        assert db_user.extra_preferences["non_vault_test_section|pass"] == "legacy_pass"
        assert "vaulttestsection|no_such_input" not in json.loads(db_user.preferences["extra_user_preferences"])

    def test_sensitive_values_are_not_serialized(self):
        email = "extra-prefs-redacted@test.gx"
        with self._different_user(email):
            self._put_prefs(
                {
                    "typed_section": {"plain_password": "hunter2", "note": "visible"},
                    "non_vault_test_section": {"user": "u", "pass": "also_hidden"},
                }
            )
            assert self._get_prefs()["typed_section"]["plain_password"] == {"is_set": True}
            preferences = self._get("users/current").json()["preferences"]
        stored = json.loads(preferences["extra_user_preferences"])
        assert stored["typed_section|note"] == "visible"
        assert "typed_section|plain_password" not in stored
        assert "non_vault_test_section|pass" not in stored
        assert self._db_user(email).extra_preferences["typed_section|plain_password"] == "hunter2"

    def test_admin_can_read_and_write_another_users_values(self):
        owner = self._setup_user("extra-prefs-admin-target@test.gx")
        url = f"users/{owner['id']}/extra_preferences"
        response = self._put(url, data={"typed_section": {"note": "set by admin"}}, json=True, admin=True)
        self._assert_status_code_is(response, 200)
        assert self._get(url, admin=True).json()["typed_section"]["note"] == "set by admin"

    def test_legacy_required_input_cannot_be_emptied(self):
        email = "extra-prefs-legacy-required@test.gx"
        user = self._setup_user(email)
        with self._different_user(email):
            response = self._put(
                f"users/{user['id']}/information/inputs", data={"non_vault_test_section|user": ""}, json=True
            )
            self._assert_status_code_is(response, 400)

    def test_purge_removes_values(self):
        email = "extra-prefs-purge@test.gx"
        user = self._setup_user(email)
        with self._different_user(email):
            self._put_prefs(
                {"typed_section": {"note": "personal", "vault_count": 3}, "vaulttestsection": {"refresh_token": "t"}}
            )
        self._assert_status_code_is(self._delete(f"users/{user['id']}", admin=True), 200)
        self._assert_status_code_is(
            self._delete(f"users/{user['id']}", data={"purge": True}, admin=True, json=True), 200
        )

        db_user = self._db_user_by_id(user["id"])
        assert db_user.purged
        assert "extra_user_preferences" not in db_user.preferences
        assert not self._read_vault(db_user, "typed_section/vault_count")
        assert not self._read_vault(db_user, "vaulttestsection/refresh_token")
        assert self._read_vault(db_user, "vaulttestsection/client_id") is None

    def _get_prefs(self):
        response = self._get("users/current")
        response = self._get(f"users/{response.json()['id']}/extra_preferences")
        self._assert_status_code_is(response, 200)
        return response.json()

    def _put_prefs(self, payload):
        user_id = self._get("users/current").json()["id"]
        return self._put(f"users/{user_id}/extra_preferences", data=payload, json=True)

    def _db_user(self, email):
        session = self._app.model.session
        session.expire_all()
        user = get_user_by_email(session, email)
        assert user
        return user

    def _db_user_by_id(self, encoded_id):
        session = self._app.model.session
        session.expire_all()
        user = session.get(User, self._app.security.decode_id(encoded_id))
        assert user
        return user

    def _read_vault(self, user, key):
        return self._app.vault.read_secret(f"user/{user.id}/preferences/{key}")


class TestExtraUserPreferencesAccountInterfaceDisabled(integration_util.IntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_account_interface"] = False
        config["user_preferences_extra_conf_path"] = EXTRA_PREFS_CONF

    def test_extra_preferences_stay_writable(self):
        with self._different_user("extra-prefs-no-account-interface@test.gx"):
            user_id = self._get("users/current").json()["id"]
            response = self._put(
                f"users/{user_id}/extra_preferences", data={"typed_section": {"note": "still writable"}}, json=True
            )
            self._assert_status_code_is(response, 200)
            assert response.json()["typed_section"]["note"] == "still writable"


class TestExtraUserPreferencesWithoutVault(integration_util.IntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["user_preferences_extra_conf_path"] = EXTRA_PREFS_CONF

    def test_vault_inputs_are_unset_and_refused(self):
        with self._different_user("extra-prefs-no-vault@test.gx"):
            user_id = self._get("users/current").json()["id"]
            response = self._get(f"users/{user_id}/extra_preferences")
            self._assert_status_code_is(response, 200)
            assert response.json()["typed_section"]["optional_token"] == {"is_set": False}

            response = self._put(
                f"users/{user_id}/extra_preferences", data={"typed_section": {"optional_token": "x"}}, json=True
            )
            self._assert_status_code_is(response, 403)
