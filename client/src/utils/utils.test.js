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

    describe("test mergeObjectListsById", () => {
        it("should merge two object lists based on the id ", () => {
            const list1 = [
                { id: "id1", name: "John" },
                { id: "id2", name: "Jane" },
                { id: "id3", name: "Bob" },
            ];
            const list2 = [
                { id: "id2", name: "Janet" },
                { id: "id4", name: "Alice" },
            ];
            const mergedList = Utils.mergeObjectListsById(list1, list2).sort((a, b) => a.id.localeCompare(b.id));
            expect(mergedList).toEqual([
                { id: "id1", name: "John" },
                { id: "id2", name: "Janet" },
                { id: "id3", name: "Bob" },
                { id: "id4", name: "Alice" },
            ]);
        });

        it("should merge two object lists and sort them based on the name in ascending order", () => {
            const list1 = [
                { id: "id1", name: "John" },
                { id: "id2", name: "Jane" },
                { id: "id3", name: "Bob" },
            ];
            const list2 = [
                { id: "id2", name: "Janet" },
                { id: "id4", name: "Alice" },
            ];
            const mergedList = Utils.mergeObjectListsById(list1, list2, "name", "asc");
            expect(mergedList).toEqual([
                { id: "id4", name: "Alice" },
                { id: "id3", name: "Bob" },
                { id: "id2", name: "Janet" },
                { id: "id1", name: "John" },
            ]);
        });

        it("should merge two object lists and sort them based on the update_time in ascending order", () => {
            const list1 = [
                { id: "id1", name: "John", update_time: "2022-04-12T03:10:01.000000" },
                { id: "id2", name: "Jane", update_time: "2023-01-05T13:10:22.000000" },
                { id: "id3", name: "Bob", update_time: "2023-04-04T13:40:31.000000" },
            ];
            const list2 = [
                { id: "id2", name: "Janet", update_time: "2023-04-05T13:20:59.541914" },
                { id: "id4", name: "Alice", update_time: "2023-02-08T13:30:00.349914" },
            ];
            const mergedList = Utils.mergeObjectListsById(list1, list2, "update_time", "asc");
            expect(mergedList).toEqual([
                { id: "id1", name: "John", update_time: "2022-04-12T03:10:01.000000" },
                { id: "id4", name: "Alice", update_time: "2023-02-08T13:30:00.349914" },
                { id: "id3", name: "Bob", update_time: "2023-04-04T13:40:31.000000" },
                { id: "id2", name: "Janet", update_time: "2023-04-05T13:20:59.541914" },
            ]);
        });
    });
});
