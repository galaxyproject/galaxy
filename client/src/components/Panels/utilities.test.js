import toolsList from "components/ToolsView/testData/toolsList";
import { createWhooshQuery, filterTools, filterToolSections } from "./utilities";

describe("test helpers in tool searching utilities", () => {
    it("test parsing helper that converts settings to whoosh query", async () => {
        const settings = {
            name: "Filter",
            id: "__FILTER_FAILED_DATASETS__",
            help: "downstream",
        };
        const q = createWhooshQuery(settings, "default", []);

        // OrGroup (at backend) on name, name_exact, description
        expect(q).toContain("name:(Filter) name_exact:(Filter) description:(Filter)");
        // AndGroup (explicit at frontend) on all other settings
        expect(q).toContain("id_exact:(__FILTER_FAILED_DATASETS__) AND help:(downstream)");
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
