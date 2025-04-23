import { type CollectionType } from "@/api/datasetCollections";

import { buildersForCollectionType, buildersForCollectionTypes } from "./collections";

describe("buildersForCollectionType", () => {
    it("should return the list builder for flat list collections", () => {
        const result = buildersForCollectionType("list" as CollectionType);
        expect(result).toEqual(["list"]);
    });

    it("should return both the obvious paired builder but the paired list builder also for mapping over", () => {
        const result = buildersForCollectionType("paired" as CollectionType);
        expect(result).toEqual(["list:paired", "paired"]);
    });

    it("should return an empty array for unknown collectionType, we have no collection builders for these", () => {
        const result = buildersForCollectionType("unknown" as CollectionType);
        expect(result).toEqual([]);
    });
});

describe("buildersForCollectionTypes", () => {
    it("should return unique builders for multiple collection types", () => {
        const collectionTypes: CollectionType[] = ["list", "paired", "list:paired"];
        const result = buildersForCollectionTypes(collectionTypes);
        expect(result).toEqual(expect.arrayContaining(["list", "paired", "list:paired"]));
        expect(result.length).toBe(3); // Ensure uniqueness
    });

    it("should return an empty array for an empty input", () => {
        const result = buildersForCollectionTypes([]);
        expect(result).toEqual([]);
    });

    it("should handle unknown collection types gracefully", () => {
        const collectionTypes: CollectionType[] = ["paired:paired:list", "list"];
        const result = buildersForCollectionTypes(collectionTypes);
        expect(result).toEqual(expect.arrayContaining(["list"]));
        expect(result.length).toBe(1);
    });
});
