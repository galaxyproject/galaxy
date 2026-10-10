import { describe, expect, it } from "vitest";

import { useKeyedObjects } from "./keyedObjects";

describe("useKeyedObjects", () => {
    it("keeps an object's key when its properties change", () => {
        const { keyObject } = useKeyedObjects();
        const object: { a: number; b: number; c?: number } = { a: 1, b: 2 };
        const originalKey = keyObject(object);

        expect(keyObject(object)).toBe(originalKey);

        object.a += 5;
        object.c = 6;

        expect(keyObject(object)).toBe(originalKey);
    });

    it("assigns a distinct key to a structured clone", () => {
        const { keyObject } = useKeyedObjects();
        const original = { d: 3 };
        const clone = structuredClone(original);

        expect(keyObject(original)).not.toBe(keyObject(clone));
    });

    it.each([
        { name: "objects with different properties", first: { a: 1 }, second: { b: 2 } },
        { name: "two empty objects", first: {}, second: {} },
    ])("assigns different keys to $name", ({ first, second }) => {
        const { keyObject } = useKeyedObjects();

        expect(keyObject(first)).not.toBe(keyObject(second));
    });
});
