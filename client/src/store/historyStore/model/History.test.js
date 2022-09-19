import { History } from "./History";

describe("History model", () => {
    const initialProps = {
        id: "abc123",
        name: "Foo",
        tags: ["a", "b", "c"],
        annotation: "I am a test history",
    };

    const h = new History(initialProps);

    describe("clone", () => {
        const c = h.clone();

        it("must be able to clone itself for use in editors", () => {
            // should be == but not ===
            expect(h).not.toBe(c);
            expect(c).toBeInstanceOf(History);
            expect(History.equals(h, c)).toBeTruthy();
        });

        it("should have the same props before and after cloning", () => {
            expect(h.id).toEqual(c.id);
            expect(h.name).toEqual(c.name);
            expect(h.tags).toEqual(c.tags);
            expect(h.annotation).toEqual(c.annotation);
        });
    });

    describe("patch", () => {
        const patchVals = {
            name: "i was patched",
            annotation: "patched annotation",
            tags: ["foo", "bar", "blech"],
        };

        const clone = h.patch(patchVals);

        it("should return a new instance of History", () => {
            expect(h).not.toBe(clone);
            expect(clone).toBeInstanceOf(History);
            expect(History.equals(h, clone)).toBeFalsy();
        });

        it("should patch in passed properties", () => {
            expect(clone.name).toEqual(patchVals.name);
            expect(clone.annotation).toEqual(patchVals.annotation);
            expect(clone.tags).toEqual(patchVals.tags);
        });
    });

    describe("equivalence comparison", () => {
        it("should recognize different props", () => {
            const hDifferent = new History({ id: "def345" });
            expect(History.equals(h, hDifferent)).toBeFalsy();
        });

        it("equivalence should work fine with cloned histories", () => {
            const clone = h.clone();
            // different object
            expect(h).not.toBe(clone);
            // but equivalent because props the same
            expect(History.equals(h, clone)).toBeTruthy();
        });

        it("should work with patch", () => {
            const clone = h.patch({ id: "floobar" });
            // different object
            expect(h).not.toBe(clone);
            // not equivalent because different val
            expect(History.equals(h, clone)).toBeFalsy();
        });
    });
});
