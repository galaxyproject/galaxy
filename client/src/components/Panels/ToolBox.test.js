import { describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import toolsList from "@/components/ToolsView/testData/toolsList";
import toolsListInPanel from "@/components/ToolsView/testData/toolsListInPanel";
import { setMockConfig } from "@/composables/__mocks__/config";

import { createSortedResultPanel, filterTools } from "./utilities";

vi.mock("@/composables/config");

setMockConfig({
    toolbox_auto_sort: true,
});

const { server, http } = useServerMock();

describe("ToolBox", () => {
    const toolsMock = toolsList.reduce((acc, item) => {
        acc[item.id] = item;
        return acc;
    }, {});
    const toolPanelMock = toolsListInPanel;
    const resultsMock = ["liftOver1", "__FILTER_EMPTY_DATASETS__", "__UNZIP_COLLECTION__"];

    it("test filter functions correctly matching: (1) Tools store array-of-objects with (2) Results array", async () => {
        server.use(
            http.untyped.get("/api/tool_panels/default", () => {
                return HttpResponse.json(toolsListInPanel);
            }),
            http.untyped.get("/api/tools", ({ request }) => {
                const url = new URL(request.url);
                if (url.searchParams.get("in_panel") === "False") {
                    return HttpResponse.json(toolsMock);
                }
                return HttpResponse.json(resultsMock);
            }),
        );
        const toolsResults = filterTools(toolsMock, resultsMock);
        const resultIds = Object.keys(toolsResults);
        expect(resultIds.length).toBe(3);
        const matchedTools = resultIds.map((id) => {
            return { id: id, sections: [], order: 0 };
        });
        const toolsResultsSection = createSortedResultPanel(matchedTools, toolPanelMock);
        expect(toolsResultsSection.idResults).toEqual(resultIds);
        const resultSectionIds = Object.keys(toolsResultsSection.resultPanel);
        expect(resultSectionIds.length).toBe(2);
    });
});
