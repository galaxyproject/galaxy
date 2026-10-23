import { describe, expect, it } from "vitest";
import { nextTick, ref } from "vue";

import { useUploadTableSorting } from "./uploadTableSorting";

interface Item {
    name: string;
    size?: number;
    content?: string;
}

function names(items: Item[]): string[] {
    return items.map((item) => item.name);
}

describe("useUploadTableSorting", () => {
    it("sorts numbers numerically and puts missing values last", () => {
        const items = ref<Item[]>([{ name: "ten", size: 10 }, { name: "none" }, { name: "two", size: 2 }]);
        const { onSortChanged } = useUploadTableSorting(items);

        onSortChanged("size", false);
        expect(names(items.value)).toEqual(["two", "ten", "none"]);

        onSortChanged("size", true);
        expect(names(items.value)).toEqual(["ten", "two", "none"]);
    });

    it("uses a column accessor when one is given", () => {
        const items = ref<Item[]>([
            { name: "long", content: "xxxx" },
            { name: "short", content: "x" },
        ]);
        const { onSortChanged } = useUploadTableSorting(items, { size: (item) => item.content?.length });

        onSortChanged("size", false);
        expect(names(items.value)).toEqual(["short", "long"]);
    });

    it("keeps the added order until a column is sorted", async () => {
        const items = ref<Item[]>([{ name: "c" }, { name: "a" }]);
        useUploadTableSorting(items);

        items.value.push({ name: "b" });
        await nextTick();

        expect(names(items.value)).toEqual(["c", "a", "b"]);
    });
});
