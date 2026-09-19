import { describe, expect, it } from "vitest";

import type { PaletteItem } from "../types";
import { findPaletteProvider, paletteProviders, parsePaletteQuery, rankPaletteItems } from "./index";
import { ACTIONS_SCOPE, PALETTE_SCOPES } from "./scopes";

function item(id: string, title: string, extras: Partial<PaletteItem> = {}): PaletteItem {
    return { id, title, ...extras };
}

/** Key of the scope a query resolves to, or undefined when it is plain text */
function scopeKey(raw: string) {
    const parsed = parsePaletteQuery(raw);
    return parsed.type === "scope" ? parsed.scope.key : undefined;
}

describe("paletteProviders", () => {
    it("serves every registered scope", () => {
        [ACTIONS_SCOPE, ...PALETTE_SCOPES].forEach((scope) => {
            expect(findPaletteProvider(scope.providerId)?.id).toBe(scope.providerId);
        });
    });

    it("registers each provider exactly once", () => {
        const ids = paletteProviders.map((provider) => provider.id);
        expect(new Set(ids).size).toBe(ids.length);
    });

    it("gives every scope variant a sectioned search", () => {
        PALETTE_SCOPES.filter((scope) => scope.variant).forEach((scope) => {
            expect(findPaletteProvider(scope.providerId)?.searchScoped).toBeTypeOf("function");
        });
    });
});

describe("parsePaletteQuery", () => {
    it("returns a plain query unscoped", () => {
        expect(parsePaletteQuery("fastqc")).toEqual({ type: "text", query: "fastqc" });
    });

    it("scopes '>' to the actions provider", () => {
        expect(parsePaletteQuery("> upload")).toMatchObject({ type: "scope", query: "upload" });
        expect(parsePaletteQuery(">")).toMatchObject({ type: "scope", query: "" });
        expect(scopeKey(">")).toBe(">");
    });

    it("scopes single-letter tokens, case-insensitively", () => {
        expect(parsePaletteQuery("t: align")).toMatchObject({ type: "scope", query: "align" });
        expect(scopeKey("t: align")).toBe("t");
        expect(scopeKey("T:align")).toBe("t");
        expect(scopeKey("w: rna")).toBe("w");
    });

    it("scopes two-letter tokens", () => {
        expect(scopeKey("hs: shared")).toBe("hs");
        expect(scopeKey("wp:")).toBe("wp");
        expect(scopeKey("pp: news")).toBe("pp");
        expect(scopeKey("it: jupyter")).toBe("it");
    });

    it("keeps unknown tokens as plain text instead of splitting them", () => {
        expect(parsePaletteQuery("name:fastqc")).toEqual({ type: "text", query: "name:fastqc" });
        expect(parsePaletteQuery("x: foo")).toEqual({ type: "text", query: "x: foo" });
        expect(parsePaletteQuery("wz: rna")).toEqual({ type: "text", query: "wz: rna" });
    });

    it("treats a lone '?' as the help request", () => {
        expect(parsePaletteQuery("?")).toEqual({ type: "help" });
        expect(parsePaletteQuery("  ?  ")).toEqual({ type: "help" });
        expect(parsePaletteQuery("? how")).toEqual({ type: "text", query: "? how" });
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
