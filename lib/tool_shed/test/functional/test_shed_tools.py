from tool_shed_client.schema.trs import (
    Tool,
    ToolClass,
)
from tool_shed_client.trs_util import encode_identifier
from ..base.api import (
    ShedApiTestCase,
    skip_if_api_v1,
)


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

    @skip_if_api_v1
    def test_trs_service_info(self):
        service_info = self.api_interactor.get("ga4gh/trs/v2/service-info")
        service_info.raise_for_status()

    @skip_if_api_v1
    def test_trs_tool_classes(self):
        classes_response = self.api_interactor.get("ga4gh/trs/v2/toolClasses")
        classes_response.raise_for_status()
        classes = classes_response.json()
        assert isinstance(classes, list)
        assert len(classes) == 1
        class0 = classes[0]
        assert ToolClass(**class0)

    @skip_if_api_v1
    def test_trs_tool_list(self):
        populator = self.populator
        repository = populator.setup_column_maker_repo(prefix="toolstrsindex")
        tool_id = populator.tool_guid(self, repository, "Add_a_column1")
        tool_shed_base, encoded_tool_id = encode_identifier(tool_id)
        url = f"ga4gh/trs/v2/tools/{encoded_tool_id}"
        tool_response = self.api_interactor.get(url)
        tool_response.raise_for_status()
        assert Tool(**tool_response.json())

    @skip_if_api_v1
    def test_trs_tool_parameter_json_schema(self):
        populator = self.populator
        repository = populator.setup_column_maker_repo(prefix="toolsparameterschema")
        tool_id = populator.tool_guid(self, repository, "Add_a_column1")
        tool_shed_base, encoded_tool_id = encode_identifier(tool_id)
        url = f"tools/{encoded_tool_id}/versions/1.1.0/parameter_request_schema"
        tool_response = self.api_interactor.get(url)
        tool_response.raise_for_status()
