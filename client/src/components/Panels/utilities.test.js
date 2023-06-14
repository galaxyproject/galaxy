import toolsList from "components/ToolsView/testData/toolsList";
import {
    createWhooshQuery,
    createWorkflowQuery,
    determineWidth,
    filterTools,
    filterToolSections,
    flattenTools,
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

const tempToolsList = [
    {
        elems: [
            {
                panel_section_name: "FASTA/FASTQ",
                description: "Extract UMI from fastq files",
                id: "toolshed.g2.bx.psu.edu/repos/iuc/umi_tools_extract/umi_tools_extract/1.1.2+galaxy2",
                name: "UMI-tools extract",
            },
            {
                panel_section_name: "FASTA/FASTQ",
                description: "Extract UMI from (fasta files)",
                id: "umi_tools_reduplicate",
                name: "UMI-tools reduplicate",
            },
        ],
        model_class: "ToolSection",
        id: "fasta/fastq",
        name: "FASTA/FASTQ",
    },
];

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
                list: toolsList,
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
                list: toolsList,
            },
            {
                // whitespace precedes to ensure query.trim() works
                q: " filter empty datasets",
                expectedResults: ["__FILTER_EMPTY_DATASETS__"],
                keys: { description: 1, name: 2, combined: 0 },
                list: toolsList,
            },
            {
                // hyphenated tool-name is searchable
                q: "uMi tools extract ",
                expectedResults: ["toolshed.g2.bx.psu.edu/repos/iuc/umi_tools_extract/umi_tools_extract/1.1.2+galaxy2"],
                keys: { description: 1, name: 2 },
                list: tempToolsList,
            },
            {
                // parenthesis is searchable
                q: "from FASTA files",
                expectedResults: ["umi_tools_reduplicate"],
                keys: { description: 1, name: 2 },
                list: tempToolsList,
            },
        ];
        searches.forEach((search) => {
            const { results } = searchToolsByKeys(flattenTools(search.list), search.keys, search.q);
            expect(results).toEqual(search.expectedResults);
        });
    });

    it("test tool fuzzy search", async () => {
        const expectedResults = ["__FILTER_FAILED_DATASETS__", "__FILTER_EMPTY_DATASETS__"];
        const keys = { description: 1, name: 2, combined: 0 };
        const filterQueries = ["Fillter", "FILYER", " Fitler", " filtr"];
        filterQueries.forEach((q) => {
            const { results, closestTerm } = searchToolsByKeys(flattenTools(toolsList), keys, q);
            expect(results).toEqual(expectedResults);
            expect(closestTerm).toEqual("filter");
        });
        const queries = ["datases from a collection", "from a colleection"];
        queries.forEach((q) => {
            const { results } = searchToolsByKeys(flattenTools(toolsList), keys, q);
            expect(results).toEqual(expectedResults);
        });
    });

    it("test tool filtering helpers on toolsList given list of ids", async () => {
        const ids = ["__FILTER_FAILED_DATASETS__", "liftOver1"];
        // check length of first section from imported const toolsList
        expect(toolsList.find((section) => section.id == "collection_operations").elems).toHaveLength(4);
        // check length of same section from filtered toolsList
        expect(
            filterToolSections(toolsList, ids).find((section) => section.id == "collection_operations").elems
        ).toHaveLength(1);
        // check length of filtered tools without sections
        expect(filterTools(toolsList, ids)).toHaveLength(2);
    });
});

describe("test helpers in workflow searching utilities", () => {
    it("test helper that creates workflow query given filters", async () => {
        const settings = {
            name: "extract",
            tag: "Genomic",
            published: null,
            shared_with_me: true,
            deleted: false,
        };
        const q = createWorkflowQuery(settings);
        expect(q).toEqual("name:extract tag:Genomic is:shared_with_me");
    });
});
