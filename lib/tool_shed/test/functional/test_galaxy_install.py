from ..base.api import ShedApiTestCase


class TestShedGalaxyInstallApi(ShedApiTestCase):
    def test_install_simple_tool(self):
        populator = self.populator
        repository = populator.setup_column_maker_repo(prefix="repoformetadata")
        owner = repository.owner
        name = repository.name
        installable_revisions = populator.get_ordered_installable_revisions(owner, name)
        latest_install_revision = installable_revisions.root[-1]
        self.install_repository(owner, name, latest_install_revision, tool_shed_url=self.url)
        response = self.galaxy_interactor._get("tools?in_panel=False")
        response.raise_for_status()
        expected_tool = populator.tool_guid(self, repository, "Add_a_column1", "1.1.0")
        tool_ids = [t["id"] for t in response.json()]
        assert expected_tool in tool_ids, f"Didn't find {expected_tool} in {tool_ids}"

    def test_install_simple_after_repository_metadata_reset(self):
        populator = self.populator
        repository = populator.setup_column_maker_repo(prefix="repoformetadata")
        owner = repository.owner
        name = repository.name
        installable_revisions = populator.get_ordered_installable_revisions(owner, name)
        latest_install_revision = installable_revisions.root[-1]
        metadata_response = populator.reset_metadata(repository)
        assert metadata_response.status == "ok"
        self.install_repository(owner, name, latest_install_revision, tool_shed_url=self.url)
        response = self.galaxy_interactor._get("tools?in_panel=False")
        response.raise_for_status()
        expected_tool = f"{self.host}:{self.port}/repos/{owner}/{name}/Add_a_column1/1.1.0"
        tool_ids = [t["id"] for t in response.json()]
        assert expected_tool in tool_ids, f"Didn't find {expected_tool} in {tool_ids}"
