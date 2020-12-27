import ListStorage from "./ListStorage";

describe("generic storage container", () => {

    const testVal = { id: 1, name: "test val 1" };

    let stash;
    beforeEach(() => {
        stash = new ListStorage(o => o.id);
    })

    it("should instantiate", () => {
        expect(stash).toBeDefined();
        expect(stash.size).toBe(0);
        expect([ ...stash ]).toEqual([]);
    })

    describe("adding an item", () => {

        it("should generate a fresh instance", () => {
            const newStash = stash.add(testVal);
            expect(newStash).toBeDefined();
            expect(newStash).not.toBe(stash);
        })

        it("should increase the size", () => {
            const newStash = stash.add(testVal);
            expect(newStash.size).toBe(1);
        })

        it("should show the item contains the item you just added", () => {
            const newStash = stash.add(testVal);
            expect(newStash.has(testVal)).toBeTruthy();
        })

        it("adding an item should return the added item when iterated over", () => {
            const newStash = stash.add(testVal);
            expect([ ...newStash ]).toEqual([testVal]);
        })
    })

    describe("deleting an item", () => {

        let addedStash;
        let deletedStash;

        beforeEach(() => {
            addedStash = stash.add(testVal);
            deletedStash = addedStash.remove(testVal);
        })

        it("should generate a fresh instance", () => {
            expect(deletedStash).toBeDefined();
            expect(deletedStash).not.toBe(addedStash);
        })

        it("should reduce the size", () => {
            expect(addedStash.size).toBe(1);
            expect(deletedStash.size).toBe(0);
        })

        it("should show the storage no longer contains the deleted item", () => {
            expect(deletedStash.has(testVal)).toBeFalsy();
        })

        it("should remove it from the iterated results", () => {
            expect([ ...addedStash ]).toEqual([testVal]);
            expect([ ...deletedStash ]).toEqual([]);
        })

    })

})

