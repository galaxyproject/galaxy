// Replacement for Skiplist, hoping native implementation will be faster
import { UpdateMap } from "./UpdateMap";

describe("UpdateMap", () => {
    let content;
    beforeEach(() => {
        content = new UpdateMap();
        content.set(100, "a");
        content.set(5, "a");
        content.set(4, "b");
        content.set(1, "e");
        content.set(3, "c");
        content.set(2, "d");
    });

    describe("sortMap", () => {
        test("it should sort a map in ascending key order", () => {
            content.sortKeys("asc");
            expect(Array.from(content.keys())).toEqual([1, 2, 3, 4, 5, 100]);
        });

        test("it should sort a map in descending key order", () => {
            content.sortKeys("desc");
            expect(Array.from(content.keys())).toEqual([100, 5, 4, 3, 2, 1]);
        });
    });

    describe("findClosestKey", () => {
        beforeEach(() => content.sortKeys("desc"));

        test("it should find an exact match", () => {
            const { key, index } = content.findClosestKey(3);
            expect(key).toEqual(3);
            expect(index).toEqual(3);
        });

        test("it should find the closest key if not an exact match (closest less than target)", () => {
            const { key, index } = content.findClosestKey(8);
            expect(key).toEqual(5);
            expect(index).toEqual(1);
        });

        test("it should find the closest key if not exact match (closest greater than target)", () => {
            const { key, index } = content.findClosestKey(80);
            expect(key).toEqual(100);
            expect(index).toEqual(0);
        });

        test("should return nulls for an empty map", () => {
            const empty = new UpdateMap();
            const { key, index } = empty.findClosestKey(100);
            expect(key).toBe(null);
            expect(index).toBe(null);
        });
    });
});
