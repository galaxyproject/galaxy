import { describe, expect, it } from "vitest";

import {
    ANY_COLLECTION_TYPE_DESCRIPTION,
    CollectionTypeDescription,
    NULL_COLLECTION_TYPE_DESCRIPTION,
} from "./collectionTypeDescription";

const ct = (collectionType: string) => new CollectionTypeDescription(collectionType);

describe("accepts (asymmetric subtype check)", () => {
    it.each(["list", "paired", "list:paired"])("%s accepts itself", (collectionType) => {
        expect(ct(collectionType).accepts(ct(collectionType))).toBe(true);
    });

    it.each([
        ["paired_or_unpaired", "paired"],
        ["list:paired_or_unpaired", "list:paired"],
        ["list", "sample_sheet"],
        ["list:paired", "sample_sheet:paired"],
    ])("%s requirement is satisfied by a %s candidate (not vice versa)", (required, candidate) => {
        expect(ct(required).accepts(ct(candidate))).toBe(true);
        expect(ct(candidate).accepts(ct(required))).toBe(false);
    });

    it("disjoint types do not accept each other", () => {
        expect(ct("paired").accepts(ct("list"))).toBe(false);
        expect(ct("list").accepts(ct("paired"))).toBe(false);
    });

    it("ANY accepts any non-null collection", () => {
        expect(ANY_COLLECTION_TYPE_DESCRIPTION.accepts(ct("list"))).toBe(true);
        expect(ANY_COLLECTION_TYPE_DESCRIPTION.accepts(NULL_COLLECTION_TYPE_DESCRIPTION)).toBe(false);
    });

    it("NULL accepts nothing", () => {
        expect(NULL_COLLECTION_TYPE_DESCRIPTION.accepts(ct("list"))).toBe(false);
        expect(NULL_COLLECTION_TYPE_DESCRIPTION.accepts(ANY_COLLECTION_TYPE_DESCRIPTION)).toBe(false);
    });
});

describe("compatible (symmetric sibling-matching check)", () => {
    it.each([
        ["list", "sample_sheet"],
        ["list:paired", "sample_sheet:paired"],
        ["paired", "paired_or_unpaired"],
        ["list:paired", "list:paired_or_unpaired"],
    ])("subtype pair %s and %s is compatible in either order", (first, second) => {
        expect(ct(first).compatible(ct(second))).toBe(true);
        expect(ct(second).compatible(ct(first))).toBe(true);
    });

    it.each(["list", "paired"])("%s is compatible with itself", (collectionType) => {
        expect(ct(collectionType).compatible(ct(collectionType))).toBe(true);
    });

    it.each([
        ["paired", "list"],
        ["list:paired", "list:list"],
    ])("disjoint types %s and %s are not compatible in either order", (first, second) => {
        expect(ct(first).compatible(ct(second))).toBe(false);
        expect(ct(second).compatible(ct(first))).toBe(false);
    });
});
