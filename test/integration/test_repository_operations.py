import os
from collections import namedtuple

from sqlalchemy import select

from galaxy.model.base import transaction
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util
from galaxy_test.driver.uses_shed import UsesShed
from tool_shed.util import hg_util

REPO_TYPE = namedtuple("REPO_TYPE", "name owner changeset")
REPO = REPO_TYPE(
    "collection_column_join",
    "iuc",
    "dfde09461b1e",  # revision 2, a known installable revision
)
REVISION_3 = "58228a4d58fe"
REVISION_4 = "071084070619"


class TestRepositoryInstallIntegrationTestCase(integration_util.IntegrationTestCase, UsesShed):
    """Test data manager installation and table reload through the API"""

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.configure_shed(config)

    def setUp(self):
        super().setUp()
        self.setup_shed_config()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def tearDown(self):
        self.reset_shed_tools()
        return super().tearDown()

    def test_repository_installation(self):
        """
        Test that we can install a given revision.
        """
        self._install_repository()

    def test_repository_uninstall(self):
        """Test that we can uninstall a repository"""
        self._install_repository()
        self._uninstall_repository()

    def test_datatype_uninstall(self):
        repo = ("devteam", "blast_datatypes", "01b38f20197e")
        self.install_repository(*repo)
        self.uninstall_repository(*repo)

    def test_package_uninstall(self):
        repo = ("iuc", "package_fastqc_0_11_4", "a8f485b2efd9")
        self.install_repository(*repo)
        self.uninstall_repository(*repo)

    def test_tool_with_package_dependency_uninstall(self):
        repo = ("devteam", "fastqc", "e7b2202befea")
        self.install_repository(*repo)
        self.uninstall_repository(*repo)

    def test_repository_update(self):
        response = self._install_repository(revision=REVISION_4, version="0.0.3", allow_upgraded=True)[0]
        assert int(response["ctx_rev"]) >= 4
        latest_revision = response["changeset_revision"]
        repo_response = self._get(f"/api/tool_shed_repositories/{response['id']}").json()
        assert repo_response["tool_shed_status"]["revision_update"] == "False"  # that should really be a boolean
        # now checkout revision 3 and attempt an update
        path_components = [
            os.path.dirname(self._app.config.shed_tool_config_file),
            "toolshed.g2.bx.psu.edu",
            "repos",
            REPO.owner,
            REPO.name,
            REVISION_3,
            REPO.name,
        ]
        revision_3_path = os.path.join(*path_components[:6])
        latest_revision_path = os.path.join(*path_components[:5] + [latest_revision])
        repository_path = os.path.join(*path_components)
        # Move repo to location expected before minor update
        os.rename(latest_revision_path, revision_3_path)
        # Checkout revision 3
        hg_util.update_repository(repository_path, ctx_rev="3")
        # change repo to revision 3 in database
        model = self._app.install_model
        tsr = model.session.scalars(select(model.ToolShedRepository).limit(1)).first()
        assert tsr.name == REPO.name
        assert tsr.changeset_revision == latest_revision
        assert int(tsr.ctx_rev) >= 4
        tsr.ctx_rev = "3"
        tsr.installed_changeset_revision = REVISION_3
        tsr.changeset_revision = REVISION_3
        session = model.context
        with transaction(session):
            session.commit()
        # update shed_tool_conf.xml to look like revision 3 was the installed_changeset_revision
        with open(self._app.config.shed_tool_config_file) as shed_config:
            shed_text = shed_config.read().replace(latest_revision, REVISION_3)
        with open(self._app.config.shed_tool_config_file, "w") as shed_config:
            shed_config.write(shed_text)
        self._get("/api/tool_shed_repositories/check_for_updates", data={"id": response["id"]}, admin=True).json()
        # At this point things should look like there is minor update available
        repo_response = self._get(f"/api/tool_shed_repositories/{response['id']}")
        repo_response.raise_for_status()
        repo_json = repo_response.json()
        assert repo_json["tool_shed_status"]["revision_update"] == "True"
        assert repo_json["changeset_revision"] == REVISION_3
        assert repo_json["ctx_rev"] == "3"
        # now install revision 4 (or newer) (a.k.a a minor update)
        response = self._install_repository(
            revision=REVISION_4, version="0.0.3", verify_tool_absent=False, allow_upgraded=True
        )[0]
        assert response["changeset_revision"] == latest_revision
        assert response["installed_changeset_revision"] == REVISION_3
        # should be 4 or newer
        assert int(response["ctx_rev"]) >= 4

    def _uninstall_repository(self):
        tool = self.get_tool()
        assert tool["version"] == "0.0.2"
        self.uninstall_repository(REPO.owner, REPO.name, REPO.changeset)
        response = self.get_tool(assert_ok=False)
        assert "err_msg" in response, f"Expected an error message after tool install but response was {response}"
        assert response["err_msg"]
        assert self.get_installed_repository_for(REPO.owner, REPO.name, REPO.changeset) is None

    def _install_repository(self, revision=None, version="0.0.2", verify_tool_absent=True, allow_upgraded=False):
        if verify_tool_absent:
            response = self.get_tool(assert_ok=False)
            assert response["err_msg"]
        owner = REPO.owner
        name = REPO.name
        revision = revision or REPO.changeset
        install_response = self.install_repository(owner, name, revision)
        tool = self.get_tool()
        assert tool.get("version") == version, tool
        if not allow_upgraded:
            install_repository = self.get_installed_repository_for(owner, name, revision)
            assert install_repository
            assert self.get_installed_repository(install_repository["id"])
        else:
            # Maybe there was a newer changeset with the same version - that is fine, just make
            # sure we installed this repo at some version.
            installed_repositories = self.index_repositories(owner, name)
            assert len(installed_repositories) > 0
        return install_response

    def get_tool(self, assert_ok=True):
        response = self._get("/api/tools/collection_column_join")
        if assert_ok:
            self._assert_status_code_is_ok(response)
        return response.json()
