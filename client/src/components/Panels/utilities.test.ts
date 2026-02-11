// eslint-disable-next-line simple-import-sort/imports
import toolsListUntyped from "@/components/ToolsView/testData/toolsList.json";
import toolsListInPanelUntyped from "@/components/ToolsView/testData/toolsListInPanel.json";
import { describe, expect, it } from "vitest";

import {
    createSortedResultPanel,
    createWhooshQuery,
    determineWidth,
    filterTools,
    getValidPanelItems,
    getValidToolsInEachSection,
    searchObjectsByKeys,
    type SearchCommonKeys,
} from "./utilities";
import type { Tool, ToolPanelItem, ToolSection, ToolSectionLabel } from "@/stores/toolStore";

describe("test helpers in tool searching utilities and panel handling", () => {
    it("panel width determination", () => {
        const widthA = determineWidth({ left: 10, right: 200 }, { left: 90 }, 20, 200, "right", 160);
        expect(widthA).toBe(120);
        const widthB = determineWidth({ left: 30, right: 250 }, { left: 60 }, 30, 500, "left", 180);
        expect(widthB).toBe(340);
    });
});

const toolsList = toolsListUntyped as unknown as Tool[];
const toolsListInPanel = toolsListInPanelUntyped as unknown as Record<string, Tool | ToolSection>;

const tempToolPanel = {
    default: {
        "fasta/fastq": {
            tools: [
                "toolshed.g2.bx.psu.edu/repos/iuc/umi_tools_extract/umi_tools_extract/1.1.2+galaxy2",
                "umi_tools_reduplicate",
            ],
            model_class: "ToolSection",
            id: "fasta/fastq",
            name: "FASTA/FASTQ",
        },
    } as unknown as Record<string, ToolSection>,
};
const tempToolsList = {
    tools: {
        "toolshed.g2.bx.psu.edu/repos/iuc/umi_tools_extract/umi_tools_extract/1.1.2+galaxy2": {
            panel_section_name: "FASTA/FASTQ",
            description: "Extract UMI from fastq files",
            id: "toolshed.g2.bx.psu.edu/repos/iuc/umi_tools_extract/umi_tools_extract/1.1.2+galaxy2",
            name: "UMI-tools extract",
        },
        umi_tools_reduplicate: {
            panel_section_name: "FASTA/FASTQ",
            description: "Extract UMI from (fasta files)",
            id: "umi_tools_reduplicate",
            name: "UMI-tools reduplicate",
        },
    } as unknown as Record<string, Tool>,
};

describe("test helpers in tool searching utilities", () => {
    // Intentionally did not import the `searchTools` function from the util file
    // to be able to test different key sort orders here.
    function searchToolsByKeys(
        tools: Tool[],
        keys: SearchCommonKeys,
        query: string,
        currentPanel: Record<string, Tool | ToolSection>,
    ): {
        results: string[];
        resultPanel: Record<string, Tool | ToolSection>;
        closestTerm: string | null;
    } {
        const { matchedResults, closestTerm } = searchObjectsByKeys<Tool>(tools, keys, query, ["name", "description"]);
        const { idResults, resultPanel } = createSortedResultPanel(matchedResults, currentPanel);
        return { results: idResults, resultPanel: resultPanel, closestTerm: closestTerm };
    }

    it("test parsing helper that converts settings to whoosh query", async () => {
        const settings = {
            name: "Filter",
            id: "__FILTER_FAILED_DATASETS__",
            help: "downstream",
            owner: "devteam",
        };
        const q = createWhooshQuery(settings);

        // OrGroup (at backend) on name, name_exact, description
        expect(q).toContain("name:(Filter) name_exact:(Filter) description:(Filter)");
        // AndGroup (explicit at frontend) on all other settings
        expect(q).toContain("id_exact:(__FILTER_FAILED_DATASETS__) AND help:(downstream) AND owner:(devteam)");
        // Combined query results in:
        expect(q).toEqual(
            "(name:(Filter) name_exact:(Filter) description:(Filter)) AND (id_exact:(__FILTER_FAILED_DATASETS__) AND help:(downstream) AND owner:(devteam) AND )",
        );
    });

    it("test tool search helper that searches for tools given keys", async () => {
        const searches: {
            q: string;
            expectedResults: string[];
            keys: SearchCommonKeys;
            tools: Tool[];
            panel: Record<string, Tool | ToolSection>;
        }[] = [
            {
                // description prioritized
                q: "collection",
                expectedResults: [
                    "__FILTER_FAILED_DATASETS__",
                    "__FILTER_EMPTY_DATASETS__",
                    "__UNZIP_COLLECTION__",
                    "__ZIP_COLLECTION__",
                ],
                keys: { description: 1, name: 0 },
                tools: toolsList,
                panel: toolsListInPanel,
            },
            {
                // name prioritized
                q: "collection",
                expectedResults: [
                    "__UNZIP_COLLECTION__",
                    "__ZIP_COLLECTION__",
                    "__FILTER_FAILED_DATASETS__",
                    "__FILTER_EMPTY_DATASETS__",
                ],
                keys: { description: 0, name: 1 },
                tools: toolsList,
                panel: toolsListInPanel,
            },
            {
                // whitespace precedes to ensure query.trim() works
                q: " filter empty datasets",
                expectedResults: ["__FILTER_EMPTY_DATASETS__"],
                keys: { description: 1, name: 2, combined: 0 },
                tools: toolsList,
                panel: toolsListInPanel,
            },
            {
                // hyphenated tool-name is searchable
                q: "uMi tools extract ",
                expectedResults: ["toolshed.g2.bx.psu.edu/repos/iuc/umi_tools_extract/umi_tools_extract/1.1.2+galaxy2"],
                keys: { description: 1, name: 2 },
                tools: Object.values(tempToolsList.tools),
                panel: tempToolPanel.default,
            },
            {
                // parenthesis (and other chars) are searchable
                q: "from FASTA:files",
                expectedResults: ["umi_tools_reduplicate"],
                keys: { description: 1, name: 2 },
                tools: Object.values(tempToolsList.tools),
                panel: tempToolPanel.default,
            },
            {
                // id is not searchable if not identified by colon
                q: "__ZIP_COLLECTION__",
                expectedResults: [],
                keys: { description: 1, name: 2 },
                tools: toolsList,
                panel: toolsListInPanel,
            },
            {
                // id is searchable if provided "id:"
                q: "id:__ZIP_COLLECTION__",
                expectedResults: ["__ZIP_COLLECTION__"],
                keys: { description: 1, name: 2 },
                tools: toolsList,
                panel: toolsListInPanel,
            },
            {
                // id is searchable if provided "tool_id:"
                q: "tool_id:umi_tools",
                expectedResults: [
                    "toolshed.g2.bx.psu.edu/repos/iuc/umi_tools_extract/umi_tools_extract/1.1.2+galaxy2",
                    "umi_tools_reduplicate",
                ],
                keys: { description: 1, name: 2 },
                tools: Object.values(tempToolsList.tools),
                panel: tempToolPanel.default,
            },
            {
                // section is searchable if provided "section:"
                q: "section:Lift-Over",
                expectedResults: ["liftOver1"],
                keys: { description: 1, name: 2 },
                tools: toolsList,
                panel: toolsListInPanel,
            },
            // if at least couple words match, return results
            {
                q: "filter datasets",
                expectedResults: ["__FILTER_FAILED_DATASETS__", "__FILTER_EMPTY_DATASETS__"],
                keys: { combined: 1, wordMatch: 0 },
                tools: toolsList,
                panel: toolsListInPanel,
            },
        ];
        searches.forEach((search) => {
            const { results } = searchToolsByKeys(search.tools, search.keys, search.q, search.panel);
            expect(results).toEqual(search.expectedResults);
        });
    });

    it("test tool fuzzy search", async () => {
        const expectedResults = ["__FILTER_FAILED_DATASETS__", "__FILTER_EMPTY_DATASETS__"];
        const keys = { description: 1, name: 2, combined: 0 };
        // Testing if just names work with DL search
        const filterQueries = ["Fillter", "FILYER", " Fitler", " filtr"];
        filterQueries.forEach((q) => {
            const { results, closestTerm } = searchToolsByKeys(toolsList, keys, q, toolsListInPanel);
            expect(results).toEqual(expectedResults);
            expect(closestTerm).toEqual("filter");
        });
        // Testing if names and description function with DL search
        let queries = ["datases from a collection", "from a colleection", "from a colleection"];
        queries.forEach((q) => {
            const { results } = searchToolsByKeys(toolsList, keys, q, toolsListInPanel);
            expect(results).toEqual(expectedResults);
        });
        // Testing if different length queries correctly trigger changes in max DL distance
        queries = ["datae", "ppasetsfrom", "datass from a cppollection"];
        queries.forEach((q) => {
            const { results } = searchToolsByKeys(toolsList, keys, q, toolsListInPanel);
            expect(results).toEqual(expectedResults);
        });
    });

    it("test tool filtering helpers on toolsList given list of ids", async () => {
        const ids = ["__FILTER_FAILED_DATASETS__", "liftOver1"];
        // check length of first section from imported const toolsList
        const collectionOperationsSection = toolsListInPanel["collection_operations"] as ToolSection;
        expect(collectionOperationsSection.tools).toHaveLength(4);
        // check length of same section from filtered toolsList
        const matchedTools = ids.map((id) => {
            return { id: id, sections: [], order: 0 };
        });
        const toolResultsPanel = createSortedResultPanel(matchedTools, toolsListInPanel);
        const toolResultsSection = toolResultsPanel.resultPanel["collection_operations"] as ToolSection;
        expect(toolResultsSection.tools).toHaveLength(1);
        // check length of filtered tools (regardless of sections)
        const toolsById = toolsList.reduce<Record<string, Tool>>((acc, item) => {
            acc[item.id] = item;
            return acc;
        }, {});
        const filteredToolIds = Object.keys(filterTools(toolsById, ids));
        expect(filteredToolIds).toHaveLength(2);
    });
});

describe("getValidToolsInEachSection", () => {
    it("filters section tools to only include valid tool IDs", () => {
        const validIds = new Set(["__FILTER_FAILED_DATASETS__", "__ZIP_COLLECTION__", "liftOver1"]);
        const entries = getValidToolsInEachSection(validIds, toolsListInPanel);

        const collectionOps = entries.find(([id]) => id === "collection_operations");
        expect(collectionOps).toBeDefined();
        const collectionSection = collectionOps![1] as ToolSection;
        expect(collectionSection.tools).toEqual(["__ZIP_COLLECTION__", "__FILTER_FAILED_DATASETS__"]);

        const liftOver = entries.find(([id]) => id === "liftOver");
        expect(liftOver).toBeDefined();
        const liftOverSection = liftOver![1] as ToolSection;
        expect(liftOverSection.tools).toEqual(["liftOver1"]);
    });

    it("removes all tools from a section when none are valid", () => {
        const validIds = new Set(["liftOver1"]);
        const entries = getValidToolsInEachSection(validIds, toolsListInPanel);

        const collectionOps = entries.find(([id]) => id === "collection_operations");
        expect(collectionOps).toBeDefined();
        const collectionSection = collectionOps![1] as ToolSection;
        expect(collectionSection.tools).toEqual([]);
    });

    it("preserves ToolSectionLabels within a section's tools array", () => {
        const label: ToolSectionLabel = {
            model_class: "ToolSectionLabel",
            id: "inner_label",
            text: "Inner Label",
        };
        const panel: Record<string, Tool | ToolSection> = {
            test_section: {
                model_class: "ToolSection",
                id: "test_section",
                name: "Test Section",
                tools: ["tool_a", label as unknown as string, "tool_b"],
            } as ToolSection,
        };
        const validIds = new Set(["tool_a"]);
        const entries = getValidToolsInEachSection(validIds, panel);

        const section = entries.find(([id]) => id === "test_section");
        expect(section).toBeDefined();
        const sectionData = section![1] as ToolSection;
        // "tool_a" is valid, the label (non-string) is kept, "tool_b" is filtered out
        expect(sectionData.tools).toHaveLength(2);
        expect(sectionData.tools![0]).toBe("tool_a");
        expect(sectionData.tools![1]).toBe(label);
    });

    it("passes through items without a tools array unchanged", () => {
        const entries = getValidToolsInEachSection(new Set(), toolsListInPanel);

        // testlabel1 is a ToolSectionLabel with no tools array
        const labelEntry = entries.find(([id]) => id === "testlabel1");
        expect(labelEntry).toBeDefined();
        const labelData = labelEntry![1] as ToolSectionLabel;
        expect(labelData.model_class).toBe("ToolSectionLabel");
        expect(labelData.id).toBe("testlabel1");
    });

    it("does not mutate the original panel sections", () => {
        const panel: Record<string, Tool | ToolSection> = {
            sec: {
                model_class: "ToolSection",
                id: "sec",
                name: "Sec",
                tools: ["tool_x", "tool_y"],
            } as ToolSection,
        };
        const originalTools = [...(panel["sec"] as ToolSection).tools!];
        getValidToolsInEachSection(new Set(["tool_x"]), panel);

        // the original section should not be modified
        expect((panel["sec"] as ToolSection).tools).toEqual(originalTools);
    });

    it("returns entries in the same order as the panel", () => {
        const entries = getValidToolsInEachSection(new Set(["__UNZIP_COLLECTION__", "liftOver1"]), toolsListInPanel);
        const ids = entries.map(([id]) => id);
        expect(ids).toEqual(["collection_operations", "liftOver", "testlabel1"]);
    });
});

describe("getValidPanelItems", () => {
    it("keeps sections with valid tools and removes empty sections", () => {
        // First pass: filter tools in sections
        const validIds = new Set(["__FILTER_FAILED_DATASETS__", "liftOver1"]);
        const sectionEntries = getValidToolsInEachSection(validIds, toolsListInPanel);

        const result = getValidPanelItems(sectionEntries, validIds);
        // collection_operations has 1 valid tool, liftOver has 1 valid tool
        expect(result["collection_operations"]).toBeDefined();
        expect(result["liftOver"]).toBeDefined();
        expect((result["collection_operations"] as ToolSection).tools).toEqual(["__FILTER_FAILED_DATASETS__"]);
        expect((result["liftOver"] as ToolSection).tools).toEqual(["liftOver1"]);
    });

    it("removes sections whose tools are all filtered out", () => {
        const validIds = new Set(["liftOver1"]);
        const sectionEntries = getValidToolsInEachSection(validIds, toolsListInPanel);

        const result = getValidPanelItems(sectionEntries, validIds);
        // collection_operations has 0 valid tools so should be removed
        expect(result["collection_operations"]).toBeUndefined();
        expect(result["liftOver"]).toBeDefined();
    });

    it("excludes sections by excludedSectionIds", () => {
        const validIds = new Set(["__FILTER_FAILED_DATASETS__", "liftOver1"]);
        const sectionEntries = getValidToolsInEachSection(validIds, toolsListInPanel);

        const result = getValidPanelItems(sectionEntries, validIds, ["liftOver"]);
        expect(result["collection_operations"]).toBeDefined();
        expect(result["liftOver"]).toBeUndefined();
    });

    it("keeps ToolSectionLabels (items without tools property)", () => {
        const validIds = new Set(["liftOver1"]);
        const sectionEntries = getValidToolsInEachSection(validIds, toolsListInPanel);

        const result = getValidPanelItems(sectionEntries, validIds);
        // testlabel1 is a ToolSectionLabel and should be kept
        expect(result["testlabel1"]).toBeDefined();
        expect((result["testlabel1"] as ToolSectionLabel).model_class).toBe("ToolSectionLabel");
    });

    it("keeps standalone Tool items when they are in validToolIdsInCurrentView", () => {
        const standaloneTool = {
            model_class: "Tool",
            id: "standalone_tool",
            name: "Standalone",
            description: "A standalone tool",
        } as unknown as Tool;

        const items: [string, ToolPanelItem][] = [
            ["standalone_tool", standaloneTool as unknown as ToolSection],
            [
                "some_section",
                {
                    model_class: "ToolSection",
                    id: "some_section",
                    name: "Some Section",
                    tools: ["standalone_tool"],
                } as ToolSection,
            ],
        ];

        const result = getValidPanelItems(items, new Set(["standalone_tool"]));
        expect(result["standalone_tool"]).toBeDefined();
        expect(result["some_section"]).toBeDefined();
    });

    it("pipeline: getValidToolsInEachSection → getValidPanelItems mirrors ToolBox.vue usage", () => {
        // Simulates the localSectionsById computed in ToolBox.vue
        const allToolIds = toolsList.map((t) => t.id);
        const sectionEntries = getValidToolsInEachSection(new Set(allToolIds), toolsListInPanel);
        const result = getValidPanelItems(sectionEntries, new Set(allToolIds));

        // All sections with tools should be present
        expect(result["collection_operations"]).toBeDefined();
        expect(result["liftOver"]).toBeDefined();
        // Label should be present
        expect(result["testlabel1"]).toBeDefined();
        // Tools should be unmodified (all are valid)
        expect((result["collection_operations"] as ToolSection).tools).toHaveLength(4);
        expect((result["liftOver"] as ToolSection).tools).toHaveLength(1);
    });

    it("pipeline with exclusions: excludes specified section ids", () => {
        const allToolIds = toolsList.map((t) => t.id);
        const sectionEntries = getValidToolsInEachSection(new Set(allToolIds), toolsListInPanel);
        const result = getValidPanelItems(sectionEntries, new Set(allToolIds), ["collection_operations"]);

        expect(result["collection_operations"]).toBeUndefined();
        expect(result["liftOver"]).toBeDefined();
        expect(result["testlabel1"]).toBeDefined();
    });

    it("returns empty object when all sections are excluded or empty", () => {
        const sectionEntries = getValidToolsInEachSection(new Set(), toolsListInPanel);
        const result = getValidPanelItems(sectionEntries, new Set());

        // Only the label should remain (no tools property)
        expect(result["collection_operations"]).toBeUndefined();
        expect(result["liftOver"]).toBeUndefined();
        expect(result["testlabel1"]).toBeDefined();
    });
});
