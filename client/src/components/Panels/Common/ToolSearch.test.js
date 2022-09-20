import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import { toolSearch } from "../utilities";

describe("ToolSearch", () => {
    const toolsMock = [
        {
            "model_class": "ToolSection",
            "id": "group_1",
            "name": "Group 1",
            "version": "",
            "description": null,
            "links": null,
            "elems": [
              {
                "model_class": "Tool1",
                "id": "tool1",
                "name": "Tool 1",
                "version": "1.0.0",
                "description": "",
                "labels": [],
                "edam_operations": [
                  "operation_3359"
                ],
                "edam_topics": [],
                "hidden": "",
                "is_workflow_compatible": true,
                "xrefs": [],
                "link": "/tool_runner?tool_id=tool1",
                "min_width": -1,
                "target": "galaxy_main",
                "panel_section_id": "group_1",
                "panel_section_name": "Group 1",
                "form_style": "regular"
              },
              {
                "model_class": "Tool2",
                "id": "tool2",
                "name": "Tool 2",
                "version": "1.0.0",
                "description": "",
                "labels": [],
                "edam_operations": [
                  "operation_3436"
                ],
                "edam_topics": [],
                "hidden": "",
                "is_workflow_compatible": true,
                "xrefs": [],
                "link": "/tool_runner?tool_id=tool2",
                "min_width": -1,
                "target": "galaxy_main",
                "panel_section_id": "group_1",
                "panel_section_name": "Group 1",
                "form_style": "regular"
              }
            ]
          },
          {
            "model_class": "ToolSection",
            "id": "group_2",
            "name": "Group 2",
            "version": "",
            "description": null,
            "links": null,
            "elems": [
              {
                "model_class": "Tool3",
                "id": "tool3",
                "name": "Tool 3",
                "version": "0.1.0",
                "description": "from dataset",
                "labels": [],
                "edam_operations": [],
                "edam_topics": [],
                "hidden": "",
                "is_workflow_compatible": true,
                "xrefs": [],
                "link": "/tool_runner?tool_id=tool3",
                "min_width": -1,
                "target": "galaxy_main",
                "panel_section_id": "group_2",
                "panel_section_name": "Group 2",
                "form_style": "special"
              }
            ]
        }
    ];
    const resultsMock = ["tool1", "tool3"];

    let axiosMock;
    let getToolSearch;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        getToolSearch = new toolSearch;
    });

    it("test filter functions correctly matching: (1) Tools store array-of-objects with (2) Results array", async () => {
        axiosMock
            .onGet(`/api/tools`)
            .replyOnce(200, toolsMock)
            .onGet(/api\/tools?.*/)
            .replyOnce(200, resultsMock);
            let toolsResults = getToolSearch.filter(toolsMock, resultsMock);
            let toolsResultsSection = getToolSearch.filterSections(toolsMock, resultsMock);
        expect(toolsResults.length).toBe(2);
        expect(toolsResultsSection.length).toBe(2);
    });
});
