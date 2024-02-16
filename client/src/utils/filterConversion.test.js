import { HistoryFilters } from "components/History/HistoryFilters";
import { PublishedWorkflowFilters } from "components/Workflow/WorkflowFilters";

describe("test filtering helpers to convert filters to filter text", () => {
    it("conversion from filters to new filter text", async () => {
        const normalized = HistoryFilters.defaultFilters;
        expect(Object.keys(normalized).length).toBe(2);
        expect(normalized["deleted"]).toBe(false);
        expect(normalized["visible"]).toBe(true);
    });

    it("verify the existence of defaults", async () => {
        let filters = {};
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
        filters = {};
        Object.entries(PublishedWorkflowFilters.defaultFilters).forEach(([key, value]) => {
            filters[key] = value;
        });
        expect(PublishedWorkflowFilters.containsDefaults(filters)).toBe(true);
        filters["published"] = !PublishedWorkflowFilters.defaultFilters.published;
        expect(PublishedWorkflowFilters.containsDefaults(filters)).toBe(false);
    });

    it("verify correct conversion of filters", async () => {
        const filters = {
            deleted: HistoryFilters.defaultFilters.deleted,
            visible: HistoryFilters.defaultFilters.visible,
            name: "name",
            other: "other",
            tag: ["tag1", "tag2"],
            genome_build: "",
            published: PublishedWorkflowFilters.defaultFilters.published,
        };
        const validHistFilters = HistoryFilters.getValidFilters(filters);
        expect(Object.keys(validHistFilters)).toEqual(["deleted", "visible", "name"]);
        const validWfFilters = PublishedWorkflowFilters.getValidFilters(filters);
        expect(Object.keys(validWfFilters)).toEqual(["deleted", "name", "tag", "published"]);

        expect(HistoryFilters.getFilterText(filters)).toBe("name:name");
        filters["visible"] = !HistoryFilters.defaultFilters.visible;
        expect(HistoryFilters.getFilterText(filters)).toBe("deleted:false visible:false name:name");
        filters["visible"] = HistoryFilters.defaultFilters.visible;
        expect(HistoryFilters.getFilterText(filters)).toBe("name:name");

        expect(PublishedWorkflowFilters.getFilterText(filters, true)).toBe("name:name tag:tag1 tag:tag2 is:published");
        delete filters["published"];
        expect(PublishedWorkflowFilters.getFilterText(filters, true)).toBe("name:name tag:tag1 tag:tag2");
    });
});

describe("test filtering helpers to convert filter text to filters", () => {
    function getFilters(filteringClass, filterText) {
        return filteringClass.getValidFilters(Object.fromEntries(filteringClass.getFiltersForText(filterText)));
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

        filterText = "";
        expect(PublishedWorkflowFilters.containsDefaults(getFilters(PublishedWorkflowFilters, filterText))).toBe(true);
        filterText = "is:published is:deleted";
        expect(PublishedWorkflowFilters.containsDefaults(getFilters(PublishedWorkflowFilters, filterText))).toBe(true);
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
            published: PublishedWorkflowFilters.defaultFilters.published,
            name: "name",
        };
        let filterText = "name:name";
        expect(getFilters(PublishedWorkflowFilters, filterText)).toEqual(filters);
        filterText = "published:false name:name";
        // filters["visible"] = !PublishedWorkflowFilters.defaultFilters.visible;
        // delete filters["deleted"];
        expect(getFilters(PublishedWorkflowFilters, filterText)).toEqual(filters);
        filterText = "name:name invalid:invalid is:deleted";
        filters["deleted"] = true;
        expect(getFilters(PublishedWorkflowFilters, filterText)).toEqual(filters);
    });
});
