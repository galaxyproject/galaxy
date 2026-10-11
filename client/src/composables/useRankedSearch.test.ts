import { describe, expect, it } from "vitest";
import { ref } from "vue";

import { useRankedSearch } from "./useRankedSearch";

function toItems(ids: string[]) {
    return ids.map((id) => ({ id, text: id }));
}

describe("useRankedSearch", () => {
    it("returns the items unchanged until a search is entered", () => {
        const items = ref(toItems(["csfasta", "fasta"]));
        const { rankedItems, onSearchChange } = useRankedSearch(items, ["text"]);

        expect(rankedItems.value).toBe(items.value);
        onSearchChange("fasta");
        expect(rankedItems.value.map((item) => item.id)).toEqual(["fasta", "csfasta"]);
        onSearchChange("");
        expect(rankedItems.value).toBe(items.value);
    });

    it("re-ranks when the items change during a search", () => {
        const items = ref(toItems(["csfasta", "fasta"]));
        const { rankedItems, onSearchChange } = useRankedSearch(items, ["text"]);

        onSearchChange("fastq");
        expect(rankedItems.value).toEqual([]);
        items.value = toItems(["fastq", "fastqsanger"]);
        expect(rankedItems.value.map((item) => item.id)).toEqual(["fastq", "fastqsanger"]);
    });
});
