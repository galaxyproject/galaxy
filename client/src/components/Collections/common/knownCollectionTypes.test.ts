import { describe, expect, it } from "vitest";

import { isValidCollectionTypeStr } from "@/components/Workflow/Editor/modules/collectionTypeDescription";

import { KNOWN_COLLECTION_TYPE_GROUPS, KNOWN_COLLECTION_TYPES } from "./knownCollectionTypes";

describe("knownCollectionTypes", () => {
    it.each(KNOWN_COLLECTION_TYPES.map((known) => known.collectionType))("%s is a valid collection type", (type) => {
        expect(isValidCollectionTypeStr(type)).toBe(true);
    });

    it("lists each collection type once", () => {
        const types = KNOWN_COLLECTION_TYPES.map((known) => known.collectionType);
        expect(new Set(types).size).toBe(types.length);
    });

    it("shows every group", () => {
        for (const group of KNOWN_COLLECTION_TYPE_GROUPS) {
            expect(KNOWN_COLLECTION_TYPES.some((known) => known.group === group)).toBe(true);
        }
    });
});
