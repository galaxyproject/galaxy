import { describe, expect, it } from "vitest";

import { CollectionTypeDescription } from "./collectionTypeDescription";

const ct = (collectionType: string) => new CollectionTypeDescription(collectionType);

describe("canMapOver over paired_or_unpaired inputs", () => {
    it("maps anything but paired over paired_or_unpaired", () => {
        expect(ct("list").canMapOver(ct("paired_or_unpaired"))).toBe(true);
        expect(ct("list:paired").canMapOver(ct("paired_or_unpaired"))).toBe(true);
        expect(ct("list:list").canMapOver(ct("paired_or_unpaired"))).toBe(true);
        expect(ct("paired").canMapOver(ct("paired_or_unpaired"))).toBe(false);
        expect(ct("paired_or_unpaired").canMapOver(ct("paired_or_unpaired"))).toBe(false);
    });
});

describe("canMapOver over compound :paired_or_unpaired inputs", () => {
    it("maps over with a remaining outer rank", () => {
        expect(ct("list:list").canMapOver(ct("list:paired_or_unpaired"))).toBe(true);
        expect(ct("list:list:paired").canMapOver(ct("list:paired_or_unpaired"))).toBe(true);
        expect(ct("list:list:list").canMapOver(ct("list:paired_or_unpaired"))).toBe(true);
    });

    it("does not map over a paired inner collection without a remaining outer rank", () => {
        expect(ct("list:paired").canMapOver(ct("list:paired_or_unpaired"))).toBe(false);
        expect(ct("paired:paired").canMapOver(ct("list:paired_or_unpaired"))).toBe(false);
    });

    it("aligns higher ranks on a rank boundary", () => {
        expect(ct("paired_or_unpaired").canMapOver(ct("paired:paired_or_unpaired"))).toBe(false);
        expect(ct("list:paired_or_unpaired").canMapOver(ct("paired:paired_or_unpaired"))).toBe(false);
        expect(ct("list:paired:paired").canMapOver(ct("paired:paired_or_unpaired"))).toBe(true);
    });

    it("does not map over without a remaining outer rank", () => {
        expect(ct("paired").canMapOver(ct("list:paired_or_unpaired"))).toBe(false);
        expect(ct("paired_or_unpaired").canMapOver(ct("list:paired_or_unpaired"))).toBe(false);
        expect(ct("list").canMapOver(ct("list:paired_or_unpaired"))).toBe(false);
        expect(ct("list").canMapOver(ct("list:list:paired_or_unpaired"))).toBe(false);
        expect(ct("list:list").canMapOver(ct("list:list:paired_or_unpaired"))).toBe(false);
    });

    it("does not map over itself", () => {
        expect(ct("list:paired_or_unpaired").canMapOver(ct("list:paired_or_unpaired"))).toBe(false);
    });
});
