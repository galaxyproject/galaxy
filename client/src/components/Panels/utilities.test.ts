import { getFakeTool } from "@tests/test-data/tools";
import { describe, expect, it } from "vitest";

import toolsListUntyped from "@/components/ToolsView/testData/toolsList.json";
import toolsListInPanelUntyped from "@/components/ToolsView/testData/toolsListInPanel.json";
import type { Tool, ToolPanelItem, ToolSection, ToolSectionLabel } from "@/stores/toolStore";

import {
    countUniqueToolsInList,
    createSortedResultPanel,
    createWhooshQuery,
    determineWidth,
    filterTools,
    getValidPanelItems,
    getValidToolsInEachSection,
    type SearchCommonKeys,
    searchObjectsByKeys,
} from "./utilities";

describe("determineWidth", () => {
    it.each([
        {
            side: "right" as const,
            bounds: { left: 10, right: 200 },
            handle: { left: 90 },
            min: 20,
            max: 200,
            current: 160,
            expected: 120,
        },
        {
            side: "left" as const,
            bounds: { left: 30, right: 250 },
            handle: { left: 60 },
            min: 30,
            max: 500,
            current: 180,
            expected: 340,
        },
    ])("resizes the $side panel to $expected", ({ bounds, handle, min, max, side, current, expected }) => {
        expect(determineWidth(bounds, handle, min, max, side, current)).toBe(expected);
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
    } satisfies Record<string, ToolSection>,
};
const tempToolsList = {
    tools: {
        "toolshed.g2.bx.psu.edu/repos/iuc/umi_tools_extract/umi_tools_extract/1.1.2+galaxy2": getFakeTool({
            panel_section_name: "FASTA/FASTQ",
            description: "Extract UMI from fastq files",
            id: "toolshed.g2.bx.psu.edu/repos/iuc/umi_tools_extract/umi_tools_extract/1.1.2+galaxy2",
            name: "UMI-tools extract",
        }),
        umi_tools_reduplicate: getFakeTool({
            panel_section_name: "FASTA/FASTQ",
            description: "Extract UMI from (fasta files)",
            id: "umi_tools_reduplicate",
            name: "UMI-tools reduplicate",
        }),
    } satisfies Record<string, Tool>,
};

describe("tool search and Whoosh queries", () => {
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

    it("combines alternative name fields with required metadata clauses", () => {
        const settings = {
            name: "Filter",
            id: "__FILTER_FAILED_DATASETS__",
            help: "downstream",
            owner: "devteam",
            tag: ["data cleanup", "collection_ops"],
        };
        const q = createWhooshQuery(settings);

        // OrGroup (at backend) on name, name_exact, description
        expect(q).toContain("name:(Filter) name_exact:(Filter) description:(Filter)");
        // AndGroup (explicit at frontend) on all other settings
        expect(q).toContain(
            'id_exact:(__FILTER_FAILED_DATASETS__) AND help:(downstream) AND owner:(devteam) AND tool_tags:("data cleanup") AND tool_tags:(collection_ops)',
        );
    });

    it.each([
        { name: "tag", settings: { tag: ["data cleanup"] }, expected: '(tool_tags:("data cleanup"))' },
        { name: "section", settings: { section: '"Get Data"' }, expected: '(section:("Get Data"))' },
    ])("builds a $name query without an empty leading clause", ({ settings, expected }) => {
        expect(createWhooshQuery(settings)).toEqual(expected);
    });

    it("counts versioned tools once when falling back to the full tools list", () => {
        const firstTool = toolsList[0]!;
        const toolsWithOlderVersion = [...toolsList, { ...firstTool, id: `${firstTool.id}/0.9`, version: "0.9" }];
        expect(countUniqueToolsInList(toolsWithOlderVersion)).toBe(toolsList.length);
    });

    it.each([
        { tag: "Get Data", expected: '(tool_tags:("get data"))' },
        { tag: "Collection_Ops", expected: "(tool_tags:(collection_ops))" },
    ])("lowercases the '$tag' clause for the Whoosh analyzer", ({ tag, expected }) => {
        expect(createWhooshQuery({ tag: [tag] })).toEqual(expected);
    });

    it("escapes backslashes and quotes in quoted tag clauses", () => {
        // A tag containing both a backslash and a double quote must be escaped
        // so the resulting Whoosh phrase is well-formed (CodeQL: incomplete
        // string escaping). Backslash must be escaped before the quote.
        expect(createWhooshQuery({ tag: ['weird \\ "tag"'] })).toEqual('(tool_tags:("weird \\\\ \\"tag\\""))');
    });

    it.each<{
        name: string;
        q: string;
        expectedResults: string[];
        keys: SearchCommonKeys;
        tools: Tool[];
        panel: Record<string, Tool | ToolSection>;
    }>([
        {
            name: "description before name",
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
            name: "name before description",
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
            name: "leading whitespace",
            q: " filter empty datasets",
            expectedResults: ["__FILTER_EMPTY_DATASETS__"],
            keys: { description: 1, name: 2, combined: 0 },
            tools: toolsList,
            panel: toolsListInPanel,
        },
        {
            name: "hyphenated tool name",
            q: "uMi tools extract ",
            expectedResults: ["toolshed.g2.bx.psu.edu/repos/iuc/umi_tools_extract/umi_tools_extract/1.1.2+galaxy2"],
            keys: { description: 1, name: 2 },
            tools: Object.values(tempToolsList.tools),
            panel: tempToolPanel.default,
        },
        {
            name: "punctuation in descriptions",
            q: "from FASTA:files",
            expectedResults: ["umi_tools_reduplicate"],
            keys: { description: 1, name: 2 },
            tools: Object.values(tempToolsList.tools),
            panel: tempToolPanel.default,
        },
        {
            name: "unprefixed ID is not searchable",
            q: "__ZIP_COLLECTION__",
            expectedResults: [],
            keys: { description: 1, name: 2 },
            tools: toolsList,
            panel: toolsListInPanel,
        },
        {
            name: "id: prefix",
            q: "id:__ZIP_COLLECTION__",
            expectedResults: ["__ZIP_COLLECTION__"],
            keys: { description: 1, name: 2 },
            tools: toolsList,
            panel: toolsListInPanel,
        },
        {
            name: "tool_id: prefix",
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
            name: "section: prefix",
            q: "section:Lift-Over",
            expectedResults: ["liftOver1"],
            keys: { description: 1, name: 2 },
            tools: toolsList,
            panel: toolsListInPanel,
        },
        {
            name: "multiple matching words",
            q: "filter datasets",
            expectedResults: ["__FILTER_FAILED_DATASETS__", "__FILTER_EMPTY_DATASETS__"],
            keys: { combined: 1, wordMatch: 0 },
            tools: toolsList,
            panel: toolsListInPanel,
        },
    ])("searches '$q' with $name", (search) => {
        const { results } = searchToolsByKeys(search.tools, search.keys, search.q, search.panel);
        expect(results).toEqual(search.expectedResults);
    });

    it.each(["Fillter", "FILYER", " Fitler", " filtr"])("corrects '%s' to the closest tool-name term", (query) => {
        const { results, closestTerm } = searchToolsByKeys(
            toolsList,
            { description: 1, name: 2, combined: 0 },
            query,
            toolsListInPanel,
        );
        expect(results).toEqual(["__FILTER_FAILED_DATASETS__", "__FILTER_EMPTY_DATASETS__"]);
        expect(closestTerm).toBe("filter");
    });

    it.each([
        { name: "misspelled dataset name", query: "datases from a collection" },
        { name: "misspelled description", query: "from a colleection" },
        { name: "repeated description lookup", query: "from a colleection" },
        { name: "short query", query: "datae" },
        { name: "joined words", query: "ppasetsfrom" },
        { name: "long query", query: "datass from a cppollection" },
    ])("fuzzy-matches $name: '$query'", ({ query }) => {
        const { results } = searchToolsByKeys(
            toolsList,
            { description: 1, name: 2, combined: 0 },
            query,
            toolsListInPanel,
        );
        expect(results).toEqual(["__FILTER_FAILED_DATASETS__", "__FILTER_EMPTY_DATASETS__"]);
    });

    it("filters result sections and tools to matching IDs", () => {
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

describe("createSortedResultPanel", () => {
    it("orders results by descending order and groups into sections", () => {
        const matchedTools = [
            { id: "__FILTER_FAILED_DATASETS__", order: 1 },
            { id: "liftOver1", order: 3 },
            { id: "__ZIP_COLLECTION__", order: 2 },
        ];
        const { idResults, resultPanel } = createSortedResultPanel(matchedTools, toolsListInPanel);

        // idResults should be sorted by order descending: liftOver1 (3), __ZIP_COLLECTION__ (2), __FILTER_FAILED_DATASETS__ (1)
        expect(idResults).toEqual(["liftOver1", "__ZIP_COLLECTION__", "__FILTER_FAILED_DATASETS__"]);

        // tools are grouped into their respective sections
        const collectionOps = resultPanel["collection_operations"] as ToolSection;
        expect(collectionOps.tools).toEqual(["__ZIP_COLLECTION__", "__FILTER_FAILED_DATASETS__"]);

        const liftOver = resultPanel["liftOver"] as ToolSection;
        expect(liftOver.tools).toEqual(["liftOver1"]);
    });

    it("does not duplicate tool ids when a tool appears in only one section", () => {
        const matchedTools = [
            { id: "__FILTER_FAILED_DATASETS__", order: 0 },
            { id: "__FILTER_FAILED_DATASETS__", order: 0 },
        ];
        const { idResults } = createSortedResultPanel(matchedTools, toolsListInPanel);
        expect(idResults).toEqual(["__FILTER_FAILED_DATASETS__"]);
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
                tools: ["tool_a", label, "tool_b"],
            },
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
            },
        };
        const originalTools = ["tool_x", "tool_y"];
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
        const standaloneTool = getFakeTool({
            model_class: "Tool",
            id: "standalone_tool",
            name: "Standalone",
            description: "A standalone tool",
        });

        const items: [string, ToolPanelItem][] = [
            ["standalone_tool", standaloneTool],
            [
                "some_section",
                {
                    model_class: "ToolSection",
                    id: "some_section",
                    name: "Some Section",
                    tools: ["standalone_tool"],
                },
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

    it("retains only labels when no tools are valid", () => {
        const sectionEntries = getValidToolsInEachSection(new Set(), toolsListInPanel);
        const result = getValidPanelItems(sectionEntries, new Set());

        // Only the label should remain (no tools property)
        expect(result["collection_operations"]).toBeUndefined();
        expect(result["liftOver"]).toBeUndefined();
        expect(result["testlabel1"]).toBeDefined();
    });
});
