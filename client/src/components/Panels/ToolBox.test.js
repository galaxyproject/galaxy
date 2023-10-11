import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { useConfig } from "composables/config";

import toolsList from "./testToolsList";
import { filterTools, filterToolSections } from "./utilities";

jest.mock("composables/config");
useConfig.mockReturnValue({
    config: {
        toolbox_auto_sort: true,
    },
    isConfigLoaded: true,
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
