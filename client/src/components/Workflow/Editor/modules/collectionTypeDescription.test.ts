import { describe, expect, it } from "vitest";

import {
    ANY_COLLECTION_TYPE_DESCRIPTION,
    CollectionTypeDescription,
    NULL_COLLECTION_TYPE_DESCRIPTION,
} from "./collectionTypeDescription";

const ct = (collectionType: string) => new CollectionTypeDescription(collectionType);

describe("accepts (asymmetric subtype check)", () => {
    it("same type accepts itself", () => {
        expect(ct("list").accepts(ct("list"))).toBe(true);
        expect(ct("paired").accepts(ct("paired"))).toBe(true);
        expect(ct("list:paired").accepts(ct("list:paired"))).toBe(true);
    });

    it("paired_or_unpaired requirement is satisfied by paired candidate (not vice versa)", () => {
        expect(ct("paired_or_unpaired").accepts(ct("paired"))).toBe(true);
        expect(ct("paired").accepts(ct("paired_or_unpaired"))).toBe(false);
        expect(ct("list:paired_or_unpaired").accepts(ct("list:paired"))).toBe(true);
        expect(ct("list:paired").accepts(ct("list:paired_or_unpaired"))).toBe(false);
    });

    it("list requirement is satisfied by sample_sheet candidate (not vice versa)", () => {
        expect(ct("list").accepts(ct("sample_sheet"))).toBe(true);
        expect(ct("sample_sheet").accepts(ct("list"))).toBe(false);
        expect(ct("list:paired").accepts(ct("sample_sheet:paired"))).toBe(true);
        expect(ct("sample_sheet:paired").accepts(ct("list:paired"))).toBe(false);
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
    it("is symmetric for subtype pairs", () => {
        // sample_sheet <-> list
        expect(ct("list").compatible(ct("sample_sheet"))).toBe(true);
        expect(ct("sample_sheet").compatible(ct("list"))).toBe(true);
        expect(ct("list:paired").compatible(ct("sample_sheet:paired"))).toBe(true);
        expect(ct("sample_sheet:paired").compatible(ct("list:paired"))).toBe(true);

        // paired <-> paired_or_unpaired
        expect(ct("paired").compatible(ct("paired_or_unpaired"))).toBe(true);
        expect(ct("paired_or_unpaired").compatible(ct("paired"))).toBe(true);
        expect(ct("list:paired").compatible(ct("list:paired_or_unpaired"))).toBe(true);
        expect(ct("list:paired_or_unpaired").compatible(ct("list:paired"))).toBe(true);
    });

    it("same type is compatible with itself", () => {
        expect(ct("list").compatible(ct("list"))).toBe(true);
        expect(ct("paired").compatible(ct("paired"))).toBe(true);
    });

    it("disjoint types are not compatible (either order)", () => {
        expect(ct("paired").compatible(ct("list"))).toBe(false);
        expect(ct("list").compatible(ct("paired"))).toBe(false);
        expect(ct("list:paired").compatible(ct("list:list"))).toBe(false);
        expect(ct("list:list").compatible(ct("list:paired"))).toBe(false);
    });
});
