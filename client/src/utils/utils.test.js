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
});
