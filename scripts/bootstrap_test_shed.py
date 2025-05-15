"""Script to bootstrap a tool shed server for development.

- Create categories.
- Create some users.
- Create some repositories
"""

import argparse
import os
import subprocess
import sys
import tempfile
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

from galaxy.tool_shed.util.hg_util import clone_repository
from galaxy.util import requests
from tool_shed.test.base.api import ensure_user_with_email
from tool_shed.test.base.api_util import (
    create_user,
    ShedApiInteractor,
)
from tool_shed.test.base.populators import ToolShedPopulator
from tool_shed_client.schema import (
    Category,
    CreateRepositoryRequest,
)

DESCRIPTION = "Script to bootstrap a tool shed server for development"
DEFAULT_USER = "jmchilton@gmail.com"
DEFAULT_USER_PASSWORD = "password123"  # it is safe because of the 123

TEST_CATEGORY_NAME = "Testing Category"
TEST_CATEGORY_DESCRIPTION = "A longer description of the testing category"

MAIN_SHED_URL = "https://toolshed.g2.bx.psu.edu/"
MAIN_SHED_API = f"{MAIN_SHED_URL}/api"

CATEGORIES_TO_COPY = ["Data Export", "Climate Analysis", "Materials science"]


def main(argv: List[str]) -> None:
    arg_parser = _arg_parser()
    namespace = arg_parser.parse_args(argv)
    populator = init_populator(namespace)

    category = populator.new_category_if_needed(
        {"name": "Invalid Test Tools", "description": "A contains a repository with invalid tools."}
    )
    populator.setup_bismark_repo(category_id=category.id)
    populator.setup_test_data_repo("0010", category_id=category.id, assert_ok=False)

    category = populator.new_category_if_needed({"name": "Test Category", "description": "A longer test description."})
    mirror_main_categories(populator)
    mirror_main_users(populator)

    populator.new_user_if_needed({"email": "bob@bobsdomain.com"})
    populator.new_user_if_needed({"email": "alice@alicesdomain.com"})
    populator.new_user_if_needed({"email": "thirduser@threeis.com"})

    populator.setup_test_data_repo("column_maker_with_readme", category_id=category.id)
    populator.setup_column_maker_repo(prefix="bootstrap", category_id=category.id)
    populator.setup_column_maker_repo(prefix="bootstrap2", category_id=category.id)

    main_categories = get_main_categories()
    for category in main_categories:
        category_id = category["id"]
        category_name = category["name"]
        if category_name in CATEGORIES_TO_COPY:
            local_category = populator.get_category_with_name(category_name)
            repos = get_main_repositories_for_category(category_id)
            for repo in repos:
                mirror_main_repository(populator, repo, local_category.id)


def get_main_categories() -> List[Dict[str, Any]]:
    main_categories_endpoint = f"{MAIN_SHED_API}/categories"
    main_categories = requests.get(main_categories_endpoint).json()
    return main_categories


def get_main_users() -> List[Dict[str, Any]]:
    main_users_endpoint = f"{MAIN_SHED_API}/users"
    main_users = requests.get(main_users_endpoint).json()
    return main_users


def get_main_repositories_for_category(category_id) -> List[Dict[str, Any]]:
    main_category_repos_endpoint = f"{MAIN_SHED_API}/categories/{category_id}/repositories"
    main_repos_for_category_response = requests.get(main_category_repos_endpoint)
    main_repos_for_category = main_repos_for_category_response.json()
    assert "repositories" in main_repos_for_category
    return main_repos_for_category["repositories"]


class RemoteToolShedPopulator(ToolShedPopulator):
    """Extend the tool shed populator with some state tracking...

    ... tailored toward bootstrapping dev instances instead of
    for tests.
    """

    _categories_by_name: Optional[Dict[str, Category]] = None
    _users_by_username: Optional[Dict[str, Dict[str, Any]]] = None
    _populators_by_username: Dict[str, "RemoteToolShedPopulator"] = {}

    def __init__(self, admin_interactor: ShedApiInteractor, user_interactor: ShedApiInteractor):
        super().__init__(admin_interactor, user_interactor)

    def populator_for_user(self, username):
        if username not in self._populators_by_username:
            mock_email = f"{username}@galaxyproject.org"
            if username not in self.users_by_username:
                user = self.new_user_if_needed({"username": username, "email": mock_email})
            else:
                user = self.users_by_username[username]
            assert user
            password = "testpass"
            api_key = self._admin_api_interactor.create_api_key(mock_email, password)
            user_interactor = ShedApiInteractor(self._admin_api_interactor.url, api_key)
            self._populators_by_username[username] = RemoteToolShedPopulator(
                self._admin_api_interactor, user_interactor
            )
        return self._populators_by_username[username]

    @property
    def categories_by_name(self) -> Dict[str, Category]:
        if self._categories_by_name is None:
            categories = self.get_categories()
            self._categories_by_name = {c.name: c for c in categories}
        return self._categories_by_name

    @property
    def users_by_username(self) -> Dict[str, Dict[str, Any]]:
        if self._users_by_username is None:
            users_response = self._api_interactor.get("users")
            if users_response.status_code == 400:
                error_response = users_response.json()
                raise Exception(str(error_response))
            users_response.raise_for_status()
            users = users_response.json()
            self._users_by_username = {u["username"]: u for u in users}
        return self._users_by_username

    def new_category_if_needed(self, as_json: Dict[str, Any]) -> Category:
        name = as_json["name"]
        description = as_json["description"]
        if name in self.categories_by_name:
            return self.categories_by_name[name]
        return self.new_category(name, description)

    def new_user_if_needed(self, as_json: Dict[str, Any]) -> Dict[str, Any]:
        if "username" not in as_json:
            email = as_json["email"]
            as_json["username"] = email.split("@", 1)[0]
        username = as_json["username"]
        if username in self.users_by_username:
            return self.users_by_username[username]
        if "email" not in as_json:
            mock_email = f"{username}@galaxyproject.org"
            as_json["email"] = mock_email
        request = {"username": username, "email": as_json["email"]}
        print(f"creating user: {username}")
        user = create_user(self._admin_api_interactor, request)
        self.users_by_username[username] = user
        return user


def mirror_main_categories(populator: RemoteToolShedPopulator):
    main_categories = get_main_categories()
    for category in main_categories:
        populator.new_category_if_needed(category)


def mirror_main_users(populator: RemoteToolShedPopulator):
    main_users = get_main_users()
    for user in main_users:
        if not isinstance(user, dict):
            print(f"Invalid user: {user} - skipping future bootstrapping may be broken in unknown ways")
            continue
        populator.new_user_if_needed(user)


def mirror_main_repository(populator: RemoteToolShedPopulator, repository: Dict[str, Any], category_id: str):
    # TODO: mirror the user
    as_dict = repository.copy()
    as_dict["category_ids"] = category_id
    as_dict["synopsis"] = repository["description"]
    request = CreateRepositoryRequest(**as_dict)
    username = repository["owner"]
    user_populator = populator.populator_for_user(username)
    new_repository = None
    try:
        new_repository = user_populator.create_repository(request)
    except AssertionError as e:
        # if the problem is just a repository already
        # exists, continue
        err_msg = str(e)
        if "already own" not in err_msg:
            raise
    if new_repository:
        name = repository["name"]
        clone_url = f"{MAIN_SHED_URL}/repos/{username}/{name}"
        temp_dir = tempfile.mkdtemp()
        clone_repository(clone_url, temp_dir)
        url_base = populator._api_interactor.hg_url_base
        prefix, rest = url_base.split("://", 1)
        target = f"{prefix}://{username}@{rest}/repos/{username}/{name}"
        try:
            _push_to(temp_dir, target)
        except Exception as e:
            print(f"Problem cloning repository {e}, continuing bootstrap though...")
            pass
        populator.reset_metadata(new_repository)


def _push_to(repo_path: str, repo_target: str) -> None:
    subprocess.check_output(["hg", "push", repo_target], cwd=repo_path)


def init_populator(namespace) -> RemoteToolShedPopulator:
    admin_interactor = ShedApiInteractor(
        namespace.shed_url,
        namespace.admin_key,
    )
    if namespace.user_key is None:
        ensure_user_with_email(admin_interactor, DEFAULT_USER, DEFAULT_USER_PASSWORD)
        user_key = admin_interactor.create_api_key(DEFAULT_USER, DEFAULT_USER_PASSWORD)
    else:
        user_key = namespace.user_key

    user_interactor = ShedApiInteractor(namespace.shed_url, user_key)
    return RemoteToolShedPopulator(
        admin_interactor,
        user_interactor,
    )


def _arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("-u", "--shed-url", default="http://localhost:9009", help="Tool Shed URL")
    parser.add_argument("-a", "--admin-key", default="tsadminkey", help="Tool Shed Admin API Key")
    parser.add_argument(
        "-k", "--user-key", default=None, help="Tool Shed User API Key (will create a new user if unspecified)"
    )
    return parser


if __name__ == "__main__":
    main(sys.argv[1:])
