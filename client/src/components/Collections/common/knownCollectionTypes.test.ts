import { describe, expect, it } from "vitest";

import { isValidCollectionTypeStr } from "@/components/Workflow/Editor/modules/collectionTypeDescription";

import {
    describeKnownCollectionType,
    findKnownCollectionTypes,
    KNOWN_COLLECTION_TYPE_GROUPS,
    KNOWN_COLLECTION_TYPES,
} from "./knownCollectionTypes";

describe("knownCollectionTypes", () => {
    it.each(KNOWN_COLLECTION_TYPES.map((known) => known.collectionType))("%s is a valid collection type", (type) => {
        expect(isValidCollectionTypeStr(type)).toBe(true);
    });

    it("lists each collection type once", () => {
        const types = KNOWN_COLLECTION_TYPES.map((known) => known.collectionType);
        expect(new Set(types).size).toBe(types.length);
    });

    it("labels and describes every collection type", () => {
        for (const known of KNOWN_COLLECTION_TYPES) {
            expect(known.label, known.collectionType).toMatch(/\S/);
            expect(known.description, known.collectionType).toMatch(/\S/);
        }
    });

    it("lists each group's collection types, in order", () => {
        expect(KNOWN_COLLECTION_TYPE_GROUPS.map(({ group }) => group)).toEqual([
            "Lists",
            "Pairs and Records",
            "Nested Lists",
            "Sample Sheets",
        ]);
        for (const { group, types } of KNOWN_COLLECTION_TYPE_GROUPS) {
            expect(types.length, group).toBeGreaterThan(0);
            expect(types.every((known) => known.group === group)).toBe(true);
        }
        expect(KNOWN_COLLECTION_TYPES).toEqual(KNOWN_COLLECTION_TYPE_GROUPS.flatMap(({ types }) => types));
        expect(KNOWN_COLLECTION_TYPES[0]).toEqual({
            collectionType: "list",
            label: "Flat List",
            description:
                "A simple flat list of datasets, each with an identifier (typically a sample name). If your data isn't nested and doesn't contain paired datasets, this is the option to choose.",
            notes: {},
            group: "Lists",
        });
    });

    it("adds the note for where the collection type is being chosen", () => {
        const [mixed] = findKnownCollectionTypes(["list:paired_or_unpaired"]);
        const forWorkflowInput = describeKnownCollectionType(mixed!, "workflow_input");
        expect(forWorkflowInput.startsWith(mixed!.description)).toBe(true);
        expect(forWorkflowInput).toContain(
            "A flat list or a list of paired datasets can also be connected to this input.",
        );
        expect(describeKnownCollectionType(mixed!, "builder")).toBe(mixed!.description);
    });

    it("finds collection types in the order asked for", () => {
        expect(findKnownCollectionTypes(["list:list", "list"]).map((known) => known.label)).toEqual([
            "Nested List of Datasets",
            "Flat List",
        ]);
    });

    it("refuses a collection type it doesn't describe", () => {
        expect(() => findKnownCollectionTypes(["list", "list:list:list"])).toThrow("list:list:list");
    });
});
