import { describe, expect, it } from "vitest";

import Utils from "./utils";

describe("utils", () => {
    describe("isEmpty", () => {
        it.each([
            { name: "an empty array", value: [], expected: true },
            { name: "an array containing undefined", value: ["data", undefined], expected: true },
            { name: "an array containing null", value: ["data", null], expected: true },
            { name: "an array containing the null placeholder", value: ["data", "__null__"], expected: true },
            { name: "an array containing the undefined placeholder", value: ["data", "__undefined__"], expected: true },
            { name: "null", value: null, expected: true },
            { name: "the null placeholder", value: "__null__", expected: true },
            { name: "the undefined placeholder", value: "__undefined__", expected: true },
            { name: "an array containing data", value: ["data"], expected: false },
            { name: "a nonzero number", value: 1, expected: false },
            { name: "zero", value: 0, expected: false },
        ])("classifies $name", ({ value, expected }) => {
            expect(Utils.isEmpty(value)).toBe(expected);
        });
    });

    describe("isJSON", () => {
        it.each([
            { name: "an object", text: "{}", expected: true },
            { name: "an array", text: "[]", expected: true },
            { name: "null", text: "null", expected: true },
            { name: "an empty string", text: "", expected: true },
            { name: "unquoted text", text: "data", expected: false },
        ])("classifies $name", ({ text, expected }) => {
            expect(Utils.isJSON(text)).toBe(expected);
        });
    });

    it("generates distinct, nonempty ids with the uid prefix", () => {
        const uid = Utils.uid();

        expect(uid).not.toBe("");
        expect(uid).toMatch(/^uid-/);
        expect(Utils.uid()).not.toBe(Utils.uid());
    });

    describe("linkify", () => {
        it.each([
            {
                name: "a standalone URL",
                text: "https://galaxyproject.org",
                expected: '<a href="https://galaxyproject.org" target="_blank">https://galaxyproject.org</a>',
            },
            {
                name: "a URL surrounded by text",
                text: "Welcome to https://galaxyproject.org today",
                expected:
                    'Welcome to <a href="https://galaxyproject.org" target="_blank">https://galaxyproject.org</a> today',
            },
            {
                name: "a domain without a protocol",
                text: "Check out galaxyproject.org",
                expected: "Check out galaxyproject.org",
            },
            {
                name: "an email address surrounded by text",
                text: "Email info@galaxyproject.org",
                expected: 'Email <a href="mailto:info@galaxyproject.org">info@galaxyproject.org</a>',
            },
        ])("formats $name", ({ text, expected }) => {
            expect(Utils.linkify(text)).toBe(expected);
        });
    });

    describe("mergeObjectListsById", () => {
        it("replaces matching ids with the new entry and keeps distinct ids", () => {
            const oldEntries = [
                { id: "id1", name: "John" },
                { id: "id2", name: "Jane" },
                { id: "id3", name: "Bob" },
            ];
            const newEntries = [
                { id: "id2", name: "Janet" },
                { id: "id4", name: "Alice" },
            ];
            const mergedList = Utils.mergeObjectListsById(oldEntries, newEntries).sort((a, b) =>
                a.id.localeCompare(b.id),
            );
            expect(mergedList).toEqual([
                { id: "id1", name: "John" },
                { id: "id2", name: "Janet" },
                { id: "id3", name: "Bob" },
                { id: "id4", name: "Alice" },
            ]);
        });

        it("sorts merged entries by ascending name", () => {
            const oldEntries = [
                { id: "id1", name: "John" },
                { id: "id2", name: "Jane" },
                { id: "id3", name: "Bob" },
            ];
            const newEntries = [
                { id: "id2", name: "Janet" },
                { id: "id4", name: "Alice" },
            ];
            const mergedList = Utils.mergeObjectListsById(oldEntries, newEntries, "name", "asc");
            expect(mergedList).toEqual([
                { id: "id4", name: "Alice" },
                { id: "id3", name: "Bob" },
                { id: "id2", name: "Janet" },
                { id: "id1", name: "John" },
            ]);
        });

        it("sorts merged entries by ascending update time", () => {
            const oldEntries = [
                { id: "id1", name: "John", update_time: "2022-04-12T03:10:01.000000" },
                { id: "id2", name: "Jane", update_time: "2023-01-05T13:10:22.000000" },
                { id: "id3", name: "Bob", update_time: "2023-04-04T13:40:31.000000" },
            ];
            const newEntries = [
                { id: "id2", name: "Janet", update_time: "2023-04-05T13:20:59.541914" },
                { id: "id4", name: "Alice", update_time: "2023-02-08T13:30:00.349914" },
            ];
            const mergedList = Utils.mergeObjectListsById(oldEntries, newEntries, "update_time", "asc");
            expect(mergedList).toEqual([
                { id: "id1", name: "John", update_time: "2022-04-12T03:10:01.000000" },
                { id: "id4", name: "Alice", update_time: "2023-02-08T13:30:00.349914" },
                { id: "id3", name: "Bob", update_time: "2023-04-04T13:40:31.000000" },
                { id: "id2", name: "Janet", update_time: "2023-04-05T13:20:59.541914" },
            ]);
        });
    });
});
