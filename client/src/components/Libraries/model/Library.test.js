import { Library } from "./Library";

describe("Library model", () => {
    test("constructor scrubs restricted prop keys before assignment", () => {
        const obj = new Library({ name: "foo", foo: 123, clone: 23, hashKey: 234234 });
        expect(obj.clone).toBeInstanceOf(Function);
    });

    test("hashKey should be different for different valid props", () => {
        const obj = new Library({ name: "foo" });
        const obj2 = new Library({ name: "bar" });
        expect(obj.hashKey).not.toEqual(obj2.hashKey);
    });

    test("hashKey should ignore restricted props", () => {
        const obj = new Library({ name: "foo", clone: 123 });
        const obj2 = new Library({ name: "foo" });
        expect(obj.hashKey).toEqual(obj2.hashKey);
    });

    test("equals should recognize 2 object with same valid props", () => {
        const obj = new Library({ name: "foo" });
        const obj2 = new Library({ name: "foo", textMatchValue: "asdfasdf" });
        const obj3 = { name: "foo", textMatchValue: "asdfasdf" };
        expect(obj.equals(obj2)).toBeTruthy();
        expect(obj.equals(obj3)).toBeTruthy();
    });

    test("equals should be false for 2 libraries with different valid props", () => {
        const obj = new Library({ name: "foo" });
        const obj2 = new Library({ name: "bar", textMatchValue: "asdfasdf" });
        const obj3 = { name: "bar", textMatchValue: "asdfasdf" };
        expect(obj.equals(obj2)).toBeFalsy();
        expect(obj.equals(obj3)).toBeFalsy();
    });
});
