import { useKeyedObjects } from "./keyedObjects";

describe("useKeyedObjects", () => {
    it("returns the same id for the same object", () => {
        const { keyObject } = useKeyedObjects();

        const obj = {
            a: 1,
            b: 2,
        } as {
            a: number;
            b: number;
            c?: number;
        };

        const keyA = keyObject(obj);
        expect(keyObject(obj)).toBe(keyA);

        obj.a += 5;
        obj["c"] = 6;

        expect(keyObject(obj)).toBe(keyA);
    });

    it("returns different ids for different objects", () => {
        const { keyObject } = useKeyedObjects();

        const objA = {
            a: 1,
        };

        const objB = {
            b: 2,
        };

        const keyA = keyObject(objA);
        const keyB = keyObject(objB);
        expect(keyA).not.toBe(keyB);

        const objD = {
            d: 3,
        };
        const objE = structuredClone(objD);
        const keyD = keyObject(objD);
        const keyE = keyObject(objE);
        expect(keyD).not.toBe(keyE);

        expect(keyObject({})).not.toBe(keyObject({}));
    });
});
