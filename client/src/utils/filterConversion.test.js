import { HistoryFilters } from "components/History/HistoryFilters";
import { WorkflowFilters } from "components/Workflow/List/WorkflowFilters";

describe("test filtering helpers to convert filters to filter text", () => {
    const MyWorkflowFilters = WorkflowFilters("my");
    const PublishedWorkflowFilters = WorkflowFilters("published");
    it("conversion from filters to new filter text", async () => {
        const normalized = HistoryFilters.defaultFilters;
        expect(Object.keys(normalized).length).toBe(2);
        expect(normalized["deleted"]).toBe(false);
        expect(normalized["visible"]).toBe(true);
    });

    it("verify the existence of defaults", async () => {
        const filters = {};
        Object.entries(HistoryFilters.defaultFilters).forEach(([key, value]) => {
            filters[key] = value;
        });
        expect(HistoryFilters.containsDefaults(filters)).toBe(true);
        filters["deleted"] = !HistoryFilters.defaultFilters.deleted;
        expect(HistoryFilters.containsDefaults(filters)).toBe(false);
        filters["deleted"] = HistoryFilters.defaultFilters.deleted;
        filters["visible"] = !HistoryFilters.defaultFilters.visible;
        expect(HistoryFilters.containsDefaults(filters)).toBe(false);
        filters["visible"] = String(HistoryFilters.defaultFilters.visible).toUpperCase();
        expect(HistoryFilters.containsDefaults(filters)).toBe(true);
    });

    it("verify correct conversion of filters", async () => {
        const filters = {
            deleted: HistoryFilters.defaultFilters.deleted,
            visible: HistoryFilters.defaultFilters.visible,
            name: "name",
            other: "other",
            tag: ["tag1", "'tag2'", "'#tag3'"],
            genome_build: "",
            published: true,
        };
        const validHistFilters = HistoryFilters.getValidFilters(filters).validFilters;
        expect(Object.keys(validHistFilters)).toEqual(["deleted", "visible", "name"]);
        const validMyWfFilters = MyWorkflowFilters.getValidFilters(filters).validFilters;
        expect(Object.keys(validMyWfFilters)).toEqual(["deleted", "name", "tag", "published"]);
        const validPubWfFilters = PublishedWorkflowFilters.getValidFilters(filters).validFilters;
        expect(Object.keys(validPubWfFilters)).toEqual(["name", "tag"]);

        expect(HistoryFilters.getFilterText(filters)).toBe("name:name");
        filters["visible"] = !HistoryFilters.defaultFilters.visible;
        expect(HistoryFilters.getFilterText(filters)).toBe("deleted:false visible:false name:name");
        filters["visible"] = HistoryFilters.defaultFilters.visible;
        expect(HistoryFilters.getFilterText(filters)).toBe("name:name");

        // non-backend filter text keeps filters as is
        expect(MyWorkflowFilters.getFilterText(filters)).toBe("name:name tag:tag1 tag:'tag2' tag:'#tag3' is:published");

        // backend filter text adjusts name tag by replacing `#` with `name:`
        expect(MyWorkflowFilters.getFilterText(filters, true)).toBe(
            "name:name tag:tag1 tag:'tag2' tag:'name:tag3' is:published"
        );

        expect(PublishedWorkflowFilters.getFilterText(filters, true)).toBe(
            "name:name tag:tag1 tag:'tag2' tag:'name:tag3'"
        );
        delete filters["published"];
        expect(MyWorkflowFilters.getFilterText(filters, true)).toBe("name:name tag:tag1 tag:'tag2' tag:'name:tag3'");
    });
});

describe("test filtering helpers to convert filter text to filters", () => {
    const PublishedWorkflowFilters = WorkflowFilters("published");
    function getFilters(filteringClass, filterText) {
        return filteringClass.getValidFilters(Object.fromEntries(filteringClass.getFiltersForText(filterText)))
            .validFilters;
    }

    it("verify the existence of defaults", async () => {
        let filterText = "";
        expect(HistoryFilters.containsDefaults(getFilters(HistoryFilters, filterText))).toBe(true);
        filterText = "deleted:true";
        expect(HistoryFilters.containsDefaults(getFilters(HistoryFilters, filterText))).toBe(false);
        filterText = "visible:false";
        expect(HistoryFilters.containsDefaults(getFilters(HistoryFilters, filterText))).toBe(false);
        filterText = "deleted:any";
        expect(HistoryFilters.containsDefaults(getFilters(HistoryFilters, filterText))).toBe(false);
        filterText = "deleted:false visible:true";
        expect(HistoryFilters.containsDefaults(getFilters(HistoryFilters, filterText))).toBe(true);
    });

    it("verify correct conversion of filterText (HistoryFilters)", async () => {
        const filters = {
            deleted: HistoryFilters.defaultFilters.deleted,
            visible: HistoryFilters.defaultFilters.visible,
            name: "name",
        };
        let filterText = "name:name";
        expect(getFilters(HistoryFilters, filterText)).toEqual(filters);
        filterText = "visible:false name:name";
        filters["visible"] = !HistoryFilters.defaultFilters.visible;
        delete filters["deleted"];
        expect(getFilters(HistoryFilters, filterText)).toEqual(filters);
        filterText = "visible:false deleted:any name:name";
        expect(getFilters(HistoryFilters, filterText)).toEqual(filters);
        filterText = "visible:false deleted:true name:name";
        filters["deleted"] = true;
        expect(getFilters(HistoryFilters, filterText)).toEqual(filters);
        filterText = "visible:false deleted:true name:name invalid:invalid";
        expect(getFilters(HistoryFilters, filterText)).toEqual(filters);
    });

    it("verify correct conversion of filterText (PublishedWorkflowFilters)", async () => {
        const filters = {
            name: "name",
        };
        let filterText = "name:name is:published";
        expect(getFilters(PublishedWorkflowFilters, filterText)).toEqual(filters);
        filterText = "published:false name:name";
        expect(getFilters(PublishedWorkflowFilters, filterText)).toEqual(filters);
        filterText = "name:name invalid:invalid user:testUser";
        filters["user"] = "testUser";
        expect(getFilters(PublishedWorkflowFilters, filterText)).toEqual(filters);
    });
});
