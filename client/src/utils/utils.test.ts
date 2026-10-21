import { describe, expect, it } from "vitest";

import { deepEach } from "./utils";

describe("deepEach", () => {
    it("visits every nested object in depth-first order without visiting the root", () => {
        const tree = { a: { b: { c: {} } } };
        const visited: object[] = [];

        deepEach(tree, (node) => {
            visited.push(node);
        });

        expect(visited).toEqual([tree.a, tree.a.b, tree.a.b.c]);
    });

    it("skips a subtree when its callback returns false and still visits its siblings", () => {
        const tree = { a: { skip: true, child: { grandchild: {} } }, b: {} };
        const visited: object[] = [];

        deepEach(tree, (node) => {
            visited.push(node);
            if ("skip" in node && node.skip) {
                return false;
            }
        });

        expect(visited).toEqual([tree.a, tree.b]);
        expect(visited).not.toContain(tree.a.child);
        expect(visited).not.toContain(tree.a.child.grandchild);
    });

    it.each([
        { name: "undefined", callbackResult: undefined },
        { name: "true", callbackResult: true },
    ])("recurses when the callback returns $name", ({ callbackResult }) => {
        const tree = { a: { b: {} }, c: { d: {} } };
        const visited: object[] = [];

        deepEach(tree, (node) => {
            visited.push(node);
            return callbackResult;
        });

        expect(visited).toEqual([tree.a, tree.a.b, tree.c, tree.c.d]);
    });
});
