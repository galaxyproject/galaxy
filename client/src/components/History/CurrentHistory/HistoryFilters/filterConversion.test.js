import { containsDefaults, getDefaults, getFilterText } from "./filterConversion";

describe("test filtering helpers to convert settings to filter text", () => {
    it("conversion from settings to new filter text", async () => {
        const normalized = getDefaults();
        expect(Object.keys(normalized).length).toBe(2);
        expect(normalized["deleted="]).toBe(false);
        expect(normalized["visible="]).toBe(true);
    });

    it("verify the existence of defaults", async () => {
        const settings = {
            "deleted=": false,
            "visible=": true,
        };
        expect(containsDefaults(settings)).toBe(true);
        settings["deleted="] = true;
        expect(containsDefaults(settings)).toBe(false);
        settings["deleted="] = false;
        settings["visible="] = false;
        expect(containsDefaults(settings)).toBe(false);
        settings["visible="] = "TRUE";
        expect(containsDefaults(settings)).toBe(true);
    });

    it("verify correct conversion of settings", async () => {
        const settings = {
            "deleted=": false,
            "visible=": true,
            "other=": "other",
            "anything=": undefined,
        };
        expect(getFilterText(settings)).toBe("other=other");
        settings["visible="] = false;
        expect(getFilterText(settings)).toBe("deleted=false visible=false other=other");
        settings["visible="] = true;
        expect(getFilterText(settings)).toBe("other=other");
    });
});
