from urllib.parse import quote

from tool_shed_client.schema.trs import (
    Tool,
    ToolClass,
    ToolVersion,
)
from tool_shed_client.trs_util import encode_identifier
from ..base.api import ShedApiTestCase


class TestShedToolsApi(ShedApiTestCase):
    def test_tool_search(self):
        populator = self.populator
        repository = populator.setup_column_maker_repo(prefix="toolsearch")
        populator.reindex()
        response = populator.tool_search_query("Compute")
        hit_count = len(response.hits)
        assert hit_count >= 1

        if hit_count == 1:
            # if running the test standalone, we know this repository was in the results
            # but if this tool has been installed a bunch by other tests - it might not be.
            tool_search_hit = response.find_search_hit(repository)
            assert tool_search_hit
            assert tool_search_hit.tool.id == "Add_a_column1"
            assert tool_search_hit.tool.name == "Compute"

        # ensure re-index doesn't modify number of hits (regression of an issue pre-Fall 2022)
        populator.reindex()
        populator.reindex()

        response = populator.tool_search_query("Compute")
        new_hit_count = len(response.hits)

        assert hit_count == new_hit_count

        if hit_count == 1:
            # if running the test standalone, we know this repository was in the results
            # but if this tool has been installed a bunch by other tests - it might not be.
            tool_search_hit = response.find_search_hit(repository)
            assert tool_search_hit

    def test_trs_service_info(self):
        service_info = self.api_interactor.get("ga4gh/trs/v2/service-info")
        service_info.raise_for_status()

    def test_trs_tool_classes(self):
        classes_response = self.api_interactor.get("ga4gh/trs/v2/toolClasses")
        classes_response.raise_for_status()
        classes = classes_response.json()
        assert isinstance(classes, list)
        assert len(classes) == 1
        class0 = classes[0]
        assert ToolClass(**class0)

    def test_trs_tool_list(self):
        populator = self.populator
        repository = populator.setup_column_maker_repo(prefix="toolstrsindex")
        tool_id = populator.tool_guid(self, repository, "Add_a_column1")
        tool_shed_base, encoded_tool_id = encode_identifier(tool_id)
        url = f"ga4gh/trs/v2/tools/{encoded_tool_id}"
        tool_response = self.api_interactor.get(url)
        tool_response.raise_for_status()
        assert Tool(**tool_response.json())

    def test_trs_tool_parameter_json_schema(self):
        populator = self.populator
        repository = populator.setup_column_maker_repo(prefix="toolsparameterschema")
        tool_id = populator.tool_guid(self, repository, "Add_a_column1")
        tool_shed_base, encoded_tool_id = encode_identifier(tool_id)
        url = f"tools/{encoded_tool_id}/versions/1.1.0/parameter_request_schema"
        tool_response = self.api_interactor.get(url)
        tool_response.raise_for_status()

    def test_tool_interop(self):
        populator = self.populator
        repository = populator.setup_column_maker_repo(prefix="toolinterop")
        tool_id = populator.tool_guid(self, repository, "Add_a_column1")
        tool_shed_base, encoded_tool_id = encode_identifier(tool_id)
        url = f"tools/{encoded_tool_id}/versions/1.1.0/interop"
        tool_response = self.api_interactor.get(url)
        tool_response.raise_for_status()
        parsed = tool_response.json()
        assert parsed["id"] == "Add_a_column1"
        assert parsed["version"] == "1.1.0"
        assert "inputs" in parsed
        assert "outputs" in parsed

    def test_tool_source(self):
        populator = self.populator
        repository = populator.setup_column_maker_repo(prefix="toolsource")
        tool_id = populator.tool_guid(self, repository, "Add_a_column1")
        tool_shed_base, encoded_tool_id = encode_identifier(tool_id)
        url = f"tools/{encoded_tool_id}/versions/1.1.0/tool_source"
        tool_response = self.api_interactor.get(url)
        tool_response.raise_for_status()
        assert tool_response.headers["language"] == "xml"
        content = tool_response.text
        assert "Add_a_column1" in content
        assert "<tool " in content

    def test_trs_stock_tools(self):
        for tool_id in [
            "__SAMPLE_SHEET_TO_TABULAR__",
            "__FILTER_FROM_FILE__",
            "__FLATTEN__",
            "Filter1",
            "sort1",
            "Show beginning1",
        ]:
            encoded_id = quote(tool_id, safe="")
            url = f"ga4gh/trs/v2/tools/{encoded_id}"
            response = self.api_interactor.get(url)
            response.raise_for_status()
            tool = Tool(**response.json())
            assert tool.url == response.url
            assert tool.id == tool_id
            assert tool.organization == "galaxyproject"
            response = self.api_interactor.get(f"{url}/versions")
            response.raise_for_status()
            versions = [ToolVersion(**version) for version in response.json()]
            assert versions == tool.versions
            assert versions
            for version in versions:
                response = self.api_interactor.get(f"tools/{encoded_id}/versions/{quote(version.id, safe='')}")
                response.raise_for_status()
                assert version.url == response.url
                parsed = response.json()
                assert parsed["id"] == tool_id
                assert parsed["version"] == version.id

    def test_trs_unknown_stock_tool(self):
        for suffix in ["", "/versions"]:
            response = self.api_interactor.get(f"ga4gh/trs/v2/tools/unknown_stock_tool{suffix}")
            assert response.status_code == 404
