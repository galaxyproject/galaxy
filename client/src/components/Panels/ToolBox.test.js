import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import toolsList from "components/ToolsView/testData/toolsList";
import toolsListInPanel from "components/ToolsView/testData/toolsListInPanel";
import { useConfig } from "composables/config";

import { createSortedResultObject, filterTools } from "./utilities";

jest.mock("composables/config");
useConfig.mockReturnValue({
    config: {
        toolbox_auto_sort: true,
    },
    isConfigLoaded: true,
});

describe("ToolBox", () => {
    const toolsMock = toolsList.reduce((acc, item) => {
        acc[item.id] = item;
        return acc;
    }, {});
    const toolPanelMock = toolsListInPanel;
    const resultsMock = ["liftOver1", "__FILTER_EMPTY_DATASETS__", "__UNZIP_COLLECTION__"];
    let axiosMock;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
    });

    it("test filter functions correctly matching: (1) Tools store array-of-objects with (2) Results array", async () => {
        axiosMock
            .onGet(`/api/tool_panels/default`)
            .replyOnce(200, toolsListInPanel)
            .onGet(`/api/tools?in_panel=False`)
            .replyOnce(200, toolsMock)
            .onGet(/api\/tools?.*/)
            .replyOnce(200, resultsMock);
        const toolsResults = filterTools(toolsMock, resultsMock);
        const resultIds = Object.keys(toolsResults);
        expect(resultIds.length).toBe(3);
        const matchedTools = resultIds.map((id) => {
            return { id: id, sections: [], order: 0 };
        });
        const toolsResultsSection = createSortedResultObject(matchedTools, toolPanelMock);
        expect(toolsResultsSection.idResults).toEqual(resultIds);
        const resultSectionIds = Object.keys(toolsResultsSection.resultPanel);
        expect(resultSectionIds.length).toBe(2);
    });
});
