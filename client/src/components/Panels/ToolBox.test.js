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
    const toolsById = toolsList.reduce((acc, item) => {
        acc[item.id] = item;
        return acc;
    }, {});
    const originalPanel = toolsListInPanel;
    const matchingToolIds = ["liftOver1", "__FILTER_EMPTY_DATASETS__", "__UNZIP_COLLECTION__"];

    it("filters matching tools and groups them into their original panel sections", async () => {
        server.use(
            http.untyped.get("/api/tool_panels/default", () => {
                return HttpResponse.json(toolsListInPanel);
            }),
            http.untyped.get("/api/tools", ({ request }) => {
                const url = new URL(request.url);
                if (url.searchParams.get("in_panel") === "False") {
                    return HttpResponse.json(toolsById);
                }
                return HttpResponse.json(matchingToolIds);
            }),
        );
        const matchingTools = filterTools(toolsById, matchingToolIds);
        const resultIds = Object.keys(matchingTools);
        expect(resultIds).toHaveLength(3);
        expect(resultIds).toEqual(matchingToolIds);
        const matchedTools = resultIds.map((id) => ({ id, order: 0 }));
        const toolsResultsSection = createSortedResultPanel(matchedTools, originalPanel);
        expect(toolsResultsSection.idResults).toEqual(resultIds);
        const resultSectionIds = Object.keys(toolsResultsSection.resultPanel);
        expect(resultSectionIds).toHaveLength(2);
        expect(toolsResultsSection.resultPanel).toMatchObject({
            liftOver: { tools: ["liftOver1"] },
            collection_operations: { tools: ["__FILTER_EMPTY_DATASETS__", "__UNZIP_COLLECTION__"] },
        });
    });
});
