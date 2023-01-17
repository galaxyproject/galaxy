import { HistoryFilters } from "components/History/HistoryFilters";

describe("test filtering helpers to convert settings to filter text", () => {
    it("conversion from settings to new filter text", async () => {
        const normalized = HistoryFilters.getDefaults();
        expect(Object.keys(normalized).length).toBe(2);
        expect(normalized["deleted:"]).toBe(false);
        expect(normalized["visible:"]).toBe(true);
    });

    it("verify the existence of defaults", async () => {
        const settings = {};
        Object.entries(HistoryFilters.defaultFilters).forEach(([key, value]) => {
            settings[`${key}:`] = value;
        });
        expect(HistoryFilters.containsDefaults(settings)).toBe(true);
        settings["deleted:"] = !HistoryFilters.defaultFilters.deleted;
        expect(HistoryFilters.containsDefaults(settings)).toBe(false);
        settings["deleted:"] = HistoryFilters.defaultFilters.deleted;
        settings["visible:"] = !HistoryFilters.defaultFilters.visible;
        expect(HistoryFilters.containsDefaults(settings)).toBe(false);
        settings["visible:"] = String(HistoryFilters.defaultFilters.visible).toUpperCase();
        expect(HistoryFilters.containsDefaults(settings)).toBe(true);
    });

    it("verify correct conversion of settings", async () => {
        const settings = {
            "deleted:": HistoryFilters.defaultFilters.deleted,
            "visible:": HistoryFilters.defaultFilters.visible,
            "other:": "other",
            "anything:": undefined,
            "value:": "",
        };
        expect(HistoryFilters.getFilterText(settings)).toBe("other:other");
        settings["visible:"] = !HistoryFilters.defaultFilters.visible;
        expect(HistoryFilters.getFilterText(settings)).toBe("deleted:false visible:false other:other");
        settings["visible:"] = HistoryFilters.defaultFilters.visible;
        expect(HistoryFilters.getFilterText(settings)).toBe("other:other");
    });
});
