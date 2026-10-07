import { describe, expect, it } from "vitest";

import { slugify } from "./slug";

describe("slugify", () => {
    it("lowercases, collapses non alphanumeric runs and trims dashes", () => {
        expect(slugify("  My New Page!! ", "page")).toBe("my-new-page");
        expect(slugify("RNA-seq 2026 — draft", "page")).toBe("rna-seq-2026-draft");
    });

    it("falls back for a text without a single usable character", () => {
        expect(slugify("???", "page")).toBe("page");
    });
});
