import { describe, expect, it } from "vitest";

import { looseEqual } from "./looseEqual";

describe("looseEqual", () => {
    it("matches a number and its string form", () => {
        expect(looseEqual(2, "2")).toBe(true);
        expect(looseEqual("2", 2)).toBe(true);
        expect(looseEqual(2, "02")).toBe(false);
    });

    it("matches objects with equal JSON forms", () => {
        expect(looseEqual({ id: 1, tags: ["a"] }, { id: 1, tags: ["a"] })).toBe(true);
        expect(looseEqual({ id: 1 }, { id: 2 })).toBe(false);
    });

    it("depends on object key order, unlike BootstrapVue", () => {
        expect(looseEqual({ a: 1, b: 2 }, { b: 2, a: 1 })).toBe(false);
    });

    it("matches arrays by JSON form, not item by item like BootstrapVue", () => {
        expect(looseEqual([1, "a"], [1, "a"])).toBe(true);
        expect(looseEqual([1], ["1"])).toBe(false);
    });

    it("never matches an object with a primitive", () => {
        expect(looseEqual({}, "[object Object]")).toBe(false);
        expect(looseEqual("[object Object]", {})).toBe(false);
    });

    it("keeps null and undefined apart from each other and from strings", () => {
        expect(looseEqual(null, null)).toBe(true);
        expect(looseEqual(undefined, undefined)).toBe(true);
        expect(looseEqual(null, undefined)).toBe(false);
        expect(looseEqual(null, "null")).toBe(false);
        expect(looseEqual(null, {})).toBe(false);
    });

    it("matches undefined and its string form, like other primitives", () => {
        expect(looseEqual(undefined, "undefined")).toBe(true);
    });
});
