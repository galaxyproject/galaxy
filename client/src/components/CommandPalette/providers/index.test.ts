import { describe, expect, it } from "vitest";

import type { PaletteItem } from "../types";
import { parsePaletteQuery, rankPaletteItems } from "./index";

function item(id: string, title: string, extras: Partial<PaletteItem> = {}): PaletteItem {
    return { id, title, ...extras };
}

describe("parsePaletteQuery", () => {
    it("returns a plain query unscoped", () => {
        expect(parsePaletteQuery("fastqc")).toEqual({ query: "fastqc" });
    });

    it("scopes '>' to the actions provider", () => {
        expect(parsePaletteQuery("> upload")).toEqual({ providerId: "actions", query: "upload" });
        expect(parsePaletteQuery(">")).toEqual({ providerId: "actions", query: "" });
    });

    it("scopes 't:' to the tools provider, case-insensitively", () => {
        expect(parsePaletteQuery("t: align")).toEqual({ providerId: "tools", query: "align" });
        expect(parsePaletteQuery("T:align")).toEqual({ providerId: "tools", query: "align" });
    });

    it("marks known-but-unavailable prefixes as reserved", () => {
        expect(parsePaletteQuery("w: rna")).toEqual({ reservedPrefix: "w", query: "rna" });
        expect(parsePaletteQuery("i:")).toEqual({ reservedPrefix: "i", query: "" });
    });

    it("leaves multi-letter 'key:value' filters untouched", () => {
        expect(parsePaletteQuery("name:fastqc")).toEqual({ query: "name:fastqc" });
    });

    it("leaves unknown single-letter prefixes untouched", () => {
        expect(parsePaletteQuery("x: foo")).toEqual({ query: "x: foo" });
    });
});

describe("rankPaletteItems", () => {
    it("drops items that do not match the query", () => {
        const items = [item("a", "FastQC"), item("b", "Upload data")];
        const ranked = rankPaletteItems(items, "fastqc");
        expect(ranked.map((i) => i.id)).toEqual(["a"]);
    });

    it("ranks exact title matches above partial matches", () => {
        const items = [item("partial", "Upload rules helper"), item("exact", "Upload")];
        const ranked = rankPaletteItems(items, "upload");
        expect(ranked[0]?.id).toBe("exact");
        expect(ranked.map((i) => i.id)).toContain("partial");
    });

    it("matches against subtitle and keywords", () => {
        const items = [
            item("a", "Preferences", { subtitle: "Manage your account settings" }),
            item("b", "About", { keywords: "version build info" }),
        ];
        expect(rankPaletteItems(items, "account").map((i) => i.id)).toEqual(["a"]);
        expect(rankPaletteItems(items, "version").map((i) => i.id)).toEqual(["b"]);
    });

    it("returns all items unranked for an empty query", () => {
        const items = [item("a", "One"), item("b", "Two")];
        expect(rankPaletteItems(items, "")).toEqual(items);
    });
});
