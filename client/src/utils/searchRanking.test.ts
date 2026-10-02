import { describe, expect, it } from "vitest";

import { rankBySearch } from "./searchRanking";

const EXTENSIONS = ["csfasta", "fasta", "fasta.gz", "fastq", "fastqsanger", "qual454", "tabular", "tsv", "vcf"].map(
    (id) => ({ id, text: id }),
);

function rank(query: string | null | undefined) {
    return rankBySearch(EXTENSIONS, query, "text").map((item) => item.id);
}

describe("rankBySearch", () => {
    it("returns all items unchanged for an empty query", () => {
        expect(rankBySearch(EXTENSIONS, "", "text")).toBe(EXTENSIONS);
        expect(rankBySearch(EXTENSIONS, "   ", "text")).toBe(EXTENSIONS);
        expect(rankBySearch(EXTENSIONS, undefined, "text")).toBe(EXTENSIONS);
        expect(rankBySearch(EXTENSIONS, null, "text")).toBe(EXTENSIONS);
    });

    it("puts an exact match first, then prefix matches, then substring matches", () => {
        expect(rank("fasta")).toEqual(["fasta", "fasta.gz", "csfasta"]);
    });

    it("ranks prefix matches above substring matches", () => {
        expect(rank("fast")).toEqual(["fasta", "fasta.gz", "fastq", "fastqsanger", "csfasta"]);
    });

    it("ranks an exact match first even when it sorts last alphabetically", () => {
        const items = ["bed", "tabular", "tsv"].map((id) => ({ id, text: id }));
        expect(rankBySearch(items, "tsv", "text").map((item) => item.id)).toEqual(["tsv"]);
        const withSuffix = ["csv.tsv", "tsv"].map((id) => ({ id, text: id }));
        expect(rankBySearch(withSuffix, "tsv", "text").map((item) => item.id)).toEqual(["tsv", "csv.tsv"]);
    });

    it("is case-insensitive and ignores surrounding whitespace", () => {
        expect(rank("  FASTA ")).toEqual(["fasta", "fasta.gz", "csfasta"]);
    });

    it("returns an empty list when nothing matches", () => {
        expect(rank("xyz")).toEqual([]);
    });

    it("uses the given label property", () => {
        const items = [
            { id: "1", name: "abc" },
            { id: "2", name: "ab" },
        ];
        expect(rankBySearch(items, "ab", "name").map((item) => item.id)).toEqual(["2", "1"]);
    });

    it("ranks an item by its best matching key", () => {
        const items = [
            { id: "hg19_rCRS", text: "Human (hg19 with rCRS)" },
            { id: "hg19", text: "Human Feb. 2009 (GRCh37/hg19) (hg19)" },
        ];
        expect(rankBySearch(items, "hg19", ["text", "id"]).map((item) => item.id)).toEqual(["hg19", "hg19_rCRS"]);
    });
});
