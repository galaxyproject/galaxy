import { describe, expect, it } from "vitest";

import { isValidCollectionTypeStr } from "@/components/Workflow/Editor/modules/collectionTypeDescription";

import {
    COLLECTION_TYPE_SHORT_LABELS,
    describeKnownCollectionType,
    findKnownCollectionType,
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
            shortLabel: "list",
            summary: { container: "list", element: "dataset", elementPlural: "datasets" },
            description:
                "A simple flat list of datasets, each with an identifier (typically a sample name). If your data isn't nested and doesn't contain paired datasets, this is the option to choose.",
            notes: {},
            group: "Lists",
        });
    });

    it("gives every collection type a short lowercase label for prose", () => {
        for (const known of KNOWN_COLLECTION_TYPES) {
            expect(known.shortLabel, known.collectionType).toMatch(/\S/);
            expect(known.shortLabel, known.collectionType).toBe(known.shortLabel.toLowerCase());
        }
        expect(COLLECTION_TYPE_SHORT_LABELS["list:paired"]).toBe("list of pairs");
    });

    it("gives every collection type a lowercase summary of its elements", () => {
        for (const { collectionType, summary } of KNOWN_COLLECTION_TYPES) {
            for (const noun of [summary.container, summary.element, summary.elementPlural]) {
                expect(noun, collectionType).toMatch(/\S/);
                expect(noun, collectionType).toBe(noun.toLowerCase());
            }
        }
        expect(findKnownCollectionType("list:record")?.summary).toEqual({
            container: "list",
            element: "record",
            elementPlural: "records",
        });
        expect(findKnownCollectionType("paired:paired")).toBeUndefined();
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

    it("says what connects to every sample sheet workflow input", () => {
        const sampleSheets = KNOWN_COLLECTION_TYPES.filter((known) => known.collectionType.startsWith("sample_sheet"));
        expect(sampleSheets).toHaveLength(4);
        for (const known of sampleSheets) {
            expect(known.notes.workflow_input).toContain("Only sample sheets can be connected");
        }
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
