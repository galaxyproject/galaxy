import { describe, expect, it } from "vitest";

import { deepEach } from "./utils";

describe("deepEach", () => {
    it("recurses into every nested object by default", () => {
        const tree = { a: { b: { c: {} } } };
        const seen: object[] = [];
        deepEach(tree, (node) => {
            seen.push(node);
        });
        // a, b, c => 3 nested objects visited
        expect(seen).toHaveLength(3);
    });

    it("halts recursion into a subtree when the callback returns false", () => {
        const tree = { a: { skip: true, child: { grandchild: {} } }, b: {} };
        const visited: object[] = [];
        deepEach(tree, (node: any) => {
            visited.push(node);
            if (node.skip) {
                return false;
            }
        });
        // a's `child`/`grandchild` are never walked; only a and b are visited
        expect(visited).toHaveLength(2);
        expect(visited.some((n: any) => n.grandchild)).toBe(false);
    });

    it("treats undefined/true returns as recurse (backward compatible)", () => {
        const tree = { a: { b: {} }, c: { d: {} } };
        const count = { undef: 0, truthy: 0 };
        deepEach(tree, () => {
            count.undef++;
        });
        deepEach(tree, () => {
            count.truthy++;
            return true;
        });
        expect(count.undef).toBe(4);
        expect(count.truthy).toBe(4);
    });
});
