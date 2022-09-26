import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import { filterToolSections, filterTools } from "../utilities";

describe("ToolBox", () => {
    const toolsMock = [
        {
            model_class: "ToolSection",
            id: "group_1",
            name: "Group 1",
            elems: [
                {
                    model_class: "Tool1",
                    id: "tool1",
                    name: "Tool 1",
                    link: "/tool_runner?tool_id=tool1",
                    panel_section_id: "group_1",
                    panel_section_name: "Group 1",
                },
                {
                    model_class: "Tool2",
                    id: "tool2",
                    name: "Tool 2",
                    link: "/tool_runner?tool_id=tool2",
                    panel_section_id: "group_1",
                    panel_section_name: "Group 1",
                },
            ],
        },
        {
            model_class: "ToolSection",
            id: "group_2",
            name: "Group 2",
            elems: [
                {
                    model_class: "Tool3",
                    id: "tool3",
                    name: "Tool 3",
                    link: "/tool_runner?tool_id=tool3",
                    panel_section_id: "group_2",
                    panel_section_name: "Group 2",
                },
            ],
        },
    ];
    const resultsMock = ["tool1", "tool3"];

    let axiosMock;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
    });

    it("test filter functions correctly matching: (1) Tools store array-of-objects with (2) Results array", async () => {
        axiosMock
            .onGet(`/api/tools`)
            .replyOnce(200, toolsMock)
            .onGet(/api\/tools?.*/)
            .replyOnce(200, resultsMock);
        const toolsResults = filterTools(toolsMock, resultsMock);
        const toolsResultsSection = filterToolSections(toolsMock, resultsMock);
        expect(toolsResults.length).toBe(2);
        expect(toolsResultsSection.length).toBe(2);
    });
});
