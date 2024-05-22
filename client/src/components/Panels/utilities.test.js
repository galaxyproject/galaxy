import toolsList from "components/ToolsView/testData/toolsList";
import toolsListInPanel from "components/ToolsView/testData/toolsListInPanel";

import {
    createSortedResultObject,
    createWhooshQuery,
    determineWidth,
    filterTools,
    searchToolsByKeys,
} from "./utilities";

describe("test helpers in tool searching utilities and panel handling", () => {
    it("panel width determination", () => {
        const widthA = determineWidth({ left: 10, right: 200 }, { left: 90 }, 20, 200, "right", 160);
        expect(widthA).toBe(120);
        const widthB = determineWidth({ left: 30, right: 250 }, { left: 60 }, 30, 500, "left", 180);
        expect(widthB).toBe(340);
    });
});

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
    },
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
    },
};

describe("test helpers in tool searching utilities", () => {
    it("test parsing helper that converts settings to whoosh query", async () => {
        const settings = {
            name: "Filter",
            id: "__FILTER_FAILED_DATASETS__",
            help: "downstream",
            owner: "devteam",
        };
        const q = createWhooshQuery(settings, "default", []);

        // OrGroup (at backend) on name, name_exact, description
        expect(q).toContain("name:(Filter) name_exact:(Filter) description:(Filter)");
        // AndGroup (explicit at frontend) on all other settings
        expect(q).toContain("id_exact:(__FILTER_FAILED_DATASETS__) AND help:(downstream) AND owner:(devteam)");
        // Combined query results in:
        expect(q).toEqual(
            "(name:(Filter) name_exact:(Filter) description:(Filter)) AND (id_exact:(__FILTER_FAILED_DATASETS__) AND help:(downstream) AND owner:(devteam) AND )"
        );
    });

    it("test tool search helper that searches for tools given keys", async () => {
        const searches = [
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
            const { results } = searchToolsByKeys(search.tools, search.keys, search.q, "default", search.panel);
            expect(results).toEqual(search.expectedResults);
        });
    });

    it("test tool fuzzy search", async () => {
        const expectedResults = ["__FILTER_FAILED_DATASETS__", "__FILTER_EMPTY_DATASETS__"];
        const keys = { description: 1, name: 2, combined: 0 };
        // Testing if just names work with DL search
        const filterQueries = ["Fillter", "FILYER", " Fitler", " filtr"];
        filterQueries.forEach((q) => {
            const { results, closestTerm } = searchToolsByKeys(toolsList, keys, q, "default", toolsListInPanel);
            expect(results).toEqual(expectedResults);
            expect(closestTerm).toEqual("filter");
        });
        // Testing if names and description function with DL search
        let queries = ["datases from a collection", "from a colleection", "from a colleection"];
        queries.forEach((q) => {
            const { results } = searchToolsByKeys(toolsList, keys, q, "default", toolsListInPanel);
            expect(results).toEqual(expectedResults);
        });
        // Testing if different length queries correctly trigger changes in max DL distance
        queries = ["datae", "ppasetsfrom", "datass from a cppollection"];
        queries.forEach((q) => {
            const { results } = searchToolsByKeys(toolsList, keys, q, "default", toolsListInPanel);
            expect(results).toEqual(expectedResults);
        });
    });

    it("test tool filtering helpers on toolsList given list of ids", async () => {
        const ids = ["__FILTER_FAILED_DATASETS__", "liftOver1"];
        // check length of first section from imported const toolsList
        expect(toolsListInPanel["collection_operations"].tools).toHaveLength(4);
        // check length of same section from filtered toolsList
        const matchedTools = ids.map((id) => {
            return { id: id, sections: [], order: 0 };
        });
        const toolResultsPanel = createSortedResultObject(matchedTools, toolsListInPanel);
        const toolResultsSection = toolResultsPanel.resultPanel["collection_operations"];
        expect(toolResultsSection.tools).toHaveLength(1);
        // check length of filtered tools (regardless of sections)
        const toolsById = toolsList.reduce((acc, item) => {
            acc[item.id] = item;
            return acc;
        }, {});
        const filteredToolIds = Object.keys(filterTools(toolsById, ids));
        expect(filteredToolIds).toHaveLength(2);
    });
});
