import Utils from "./utils";

describe("test utils", () => {
    it("test isEmpty", async () => {
        expect(Utils.isEmpty([])).toBe(true); //  "Empty array");
        expect(Utils.isEmpty(["data", undefined])).toBe(true); // , "Array contains `undefined`");
        expect(Utils.isEmpty(["data", null])).toBe(true); //, "Array contains `null`");
        expect(Utils.isEmpty(["data", "__null__"])).toBe(true); // , "Array contains `__null__`");
        expect(Utils.isEmpty(["data", "__undefined__"])).toBe(true); // , "Array contains `__undefined__`");
        expect(Utils.isEmpty(null)).toBe(true); //, "Array is null");
        expect(Utils.isEmpty("__null__")).toBe(true); //, "Array is __null__");
        expect(Utils.isEmpty("__undefined__")).toBe(true); //, "Array is __undefined__");
        expect(Utils.isEmpty(["data"])).toBe(false); //, "Array contains `data`");
        expect(Utils.isEmpty(1)).toBe(false); //, "Value is int");
        expect(Utils.isEmpty(0)).toBe(false); //, "Value is zero");
    });

    it("test isJSON", async () => {
        expect(Utils.isJSON("{}")).toBe(true); //, "JSON is {}");
        expect(Utils.isJSON("[]")).toBe(true); //, "JSON is []");
        expect(Utils.isJSON("null")).toBe(true); //, "JSON is null");
        expect(Utils.isJSON("")).toBe(true); //, "JSON is empty");
        expect(Utils.isJSON("data")).toBe(false); //, "JSON is data");
    });

    it("test uid", async () => {
        const uid = Utils.uid();
        expect(uid).not.toBe(""); //, "UID is not empty");
        expect(uid).toMatch(/^uid-/); //, "UID starts with uid-");
        expect(Utils.uid()).not.toBe(Utils.uid()); //, "UID is unique");
    });

    it("test linkify", async () => {
        expect(Utils.linkify("https://galaxyproject.org")).toBe(
            '<a href="https://galaxyproject.org" target="_blank">https://galaxyproject.org</a>'
        );
        expect(Utils.linkify("Welcome to https://galaxyproject.org today")).toBe(
            'Welcome to <a href="https://galaxyproject.org" target="_blank">https://galaxyproject.org</a> today'
        );
        expect(Utils.linkify("Check out galaxyproject.org")).toBe("Check out galaxyproject.org");
        expect(Utils.linkify("Email info@galaxyproject.org")).toBe(
            'Email <a href="mailto:info@galaxyproject.org">info@galaxyproject.org</a>'
        );
    });
});
