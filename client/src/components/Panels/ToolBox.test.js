import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import { filterToolSections, filterTools } from "./utilities";
import toolsList from "./testToolsList";
import { useConfig } from "composables/config";

jest.mock("composables/config");
useConfig.mockReturnValue({
    config: {
        toolbox_auto_sort: true,
    },
    isLoaded: true,
});

describe("ToolBox", () => {
    const toolsMock = toolsList;
    const resultsMock = ["join1", "join_collections", "find1"];
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
        expect(toolsResults.length).toBe(3);
        expect(toolsResultsSection.length).toBe(2);
    });
});
