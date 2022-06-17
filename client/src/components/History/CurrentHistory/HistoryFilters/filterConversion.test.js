import { defaultFilters } from "store/historyStore/model/filtering";
import { containsDefaults, getDefaults, getFilterText } from "./filterConversion";

describe("test filtering helpers to convert settings to filter text", () => {
    it("conversion from settings to new filter text", async () => {
        const normalized = getDefaults();
        expect(Object.keys(normalized).length).toBe(2);
        expect(normalized["deleted:"]).toBe(false);
        expect(normalized["visible:"]).toBe(true);
    });

    it("verify the existence of defaults", async () => {
        const settings = {};
        Object.entries(defaultFilters).forEach(([key, value]) => {
            settings[`${key}:`] = value;
        });
        expect(containsDefaults(settings)).toBe(true);
        settings["deleted:"] = !defaultFilters.deleted;
        expect(containsDefaults(settings)).toBe(false);
        settings["deleted:"] = defaultFilters.deleted;
        settings["visible:"] = !defaultFilters.visible;
        expect(containsDefaults(settings)).toBe(false);
        settings["visible:"] = String(defaultFilters.visible).toUpperCase();
        expect(containsDefaults(settings)).toBe(true);
    });

    it("verify correct conversion of settings", async () => {
        const settings = {
            "deleted:": defaultFilters.deleted,
            "visible:": defaultFilters.visible,
            "other:": "other",
            "anything:": undefined,
            "value:": "",
        };
        expect(getFilterText(settings)).toBe("other:other");
        settings["visible:"] = !defaultFilters.visible;
        expect(getFilterText(settings)).toBe("deleted:false visible:false other:other");
        settings["visible:"] = defaultFilters.visible;
        expect(getFilterText(settings)).toBe("other:other");
    });
});
