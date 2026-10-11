import { describe, expect, it } from "vitest";

import { buildSearchIndex, type FilterField, rankSearchIndex } from "./filterFunction";

const EXTENSIONS = ["csfasta", "fasta", "fasta.gz", "fastq", "fastqsanger", "qual454", "tabular", "tsv", "vcf"].map(
    (id) => ({ id, text: id }),
);

function runFilter<O extends object>(query: string, items: O[], fields: FilterField<O>[]) {
    return rankSearchIndex(buildSearchIndex(items, fields), query);
}

function rank(query: string) {
    return runFilter(query, EXTENSIONS, ["text"]).map((item) => item.id);
}

describe("rankSearchIndex", () => {
    it("returns all items for an empty query", () => {
        expect(runFilter("", EXTENSIONS, ["text"])).toEqual(EXTENSIONS);
        expect(runFilter("   ", EXTENSIONS, ["text"])).toEqual(EXTENSIONS);
    });

    it("puts an exact match first, then prefix matches, then substring matches", () => {
        expect(rank("fasta")).toEqual(["fasta", "fasta.gz", "csfasta"]);
    });

    it("ranks prefix matches above substring matches", () => {
        expect(rank("fast")).toEqual(["fasta", "fasta.gz", "fastq", "fastqsanger", "csfasta"]);
    });

    it("ranks an exact match first even when it sorts last alphabetically", () => {
        const items = ["bed", "tabular", "tsv"].map((id) => ({ id, text: id }));
        expect(runFilter("tsv", items, ["text"]).map((item) => item.id)).toEqual(["tsv"]);
        const withSuffix = ["csv.tsv", "tsv"].map((id) => ({ id, text: id }));
        expect(runFilter("tsv", withSuffix, ["text"]).map((item) => item.id)).toEqual(["tsv", "csv.tsv"]);
    });

    it("is case-insensitive and ignores surrounding whitespace", () => {
        expect(rank("  FASTA ")).toEqual(["fasta", "fasta.gz", "csfasta"]);
    });

    it("returns an empty list when nothing matches", () => {
        expect(rank("xyz")).toEqual([]);
    });

    it("ranks an item by its best matching field", () => {
        const items = [
            { id: "hg19_rCRS", text: "Human (hg19 with rCRS)" },
            { id: "hg19", text: "Human Feb. 2009 (GRCh37/hg19) (hg19)" },
        ];
        expect(runFilter("hg19", items, ["text", "id"]).map((item) => item.id)).toEqual(["hg19", "hg19_rCRS"]);
    });

    it("matches string values in nested array fields", () => {
        const items = [
            { label: "first", value: { tags: ["name:other"] } },
            { label: "second", value: { tags: ["group:x", "name:sample"] } },
        ];
        expect(runFilter("name:sample", items, ["label", ["value", "tags"]]).map((item) => item.label)).toEqual([
            "second",
        ]);
    });
});
