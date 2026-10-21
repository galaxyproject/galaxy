import { describe, expect, it } from "vitest";
import { computed, ref } from "vue";

import { usePagination } from "./pagination";

describe("usePagination", () => {
    it("starts on the first page with the default page size of 24", () => {
        const items = ref([1, 2, 3, 4, 5]);
        const { paginatedItems, currentPage, itemsPerPage } = usePagination(items);

        expect(currentPage.value).toBe(1);
        expect(itemsPerPage.value).toBe(24);
        expect(paginatedItems.value).toEqual([1, 2, 3, 4, 5]);
    });

    it.each([
        { name: "first", page: 1, expected: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] },
        { name: "second", page: 2, expected: [11, 12, 13, 14, 15, 16, 17, 18, 19, 20] },
        { name: "last full", page: 5, expected: [41, 42, 43, 44, 45, 46, 47, 48, 49, 50] },
    ])("returns the $name page of 50 items", ({ page, expected }) => {
        const items = ref(Array.from({ length: 50 }, (_, i) => i + 1));
        const { paginatedItems, currentPage, onPageChange } = usePagination(items, { itemsPerPage: 10 });
        expect(paginatedItems.value).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);

        onPageChange(page);

        expect(currentPage.value).toBe(page);
        expect(paginatedItems.value).toEqual(expected);
    });

    it("shows pagination after the items exceed the configured page size", () => {
        const items = ref([1, 2, 3]);
        const { showPagination } = usePagination(items, { itemsPerPage: 5 });

        expect(showPagination.value).toBe(false);

        items.value = Array.from({ length: 10 }, (_, i) => i + 1);
        expect(showPagination.value).toBe(true);
    });

    it("resets the current page after navigating to page three", () => {
        const items = ref(Array.from({ length: 30 }, (_, i) => i + 1));
        const { currentPage, onPageChange, resetPage } = usePagination(items, { itemsPerPage: 10 });

        onPageChange(3);
        expect(currentPage.value).toBe(3);

        resetPage();
        expect(currentPage.value).toBe(1);
    });

    it("updates the total after items are appended", () => {
        const items = ref([1, 2, 3]);
        const { totalItems } = usePagination(items);

        expect(totalItems.value).toBe(3);

        items.value = [...items.value, 4, 5];
        expect(totalItems.value).toBe(5);
    });

    it("paginates the results of a computed filter", () => {
        const baseItems = ref([1, 2, 3, 4, 5, 6]);
        const filteredItems = computed(() => baseItems.value.filter((item) => item > 3));
        const { paginatedItems, totalItems } = usePagination(filteredItems, { itemsPerPage: 2 });

        expect(totalItems.value).toBe(3);
        expect(paginatedItems.value).toEqual([4, 5]);
    });

    it("returns no items and hides pagination for an empty list", () => {
        const items = ref<number[]>([]);
        const { paginatedItems, totalItems, showPagination } = usePagination(items);

        expect(paginatedItems.value).toEqual([]);
        expect(totalItems.value).toBe(0);
        expect(showPagination.value).toBe(false);
    });

    it("returns the remaining five items on the last partial page", () => {
        const items = ref(Array.from({ length: 25 }, (_, i) => i + 1));
        const { paginatedItems, onPageChange } = usePagination(items, { itemsPerPage: 10 });

        onPageChange(3);
        expect(paginatedItems.value).toEqual([21, 22, 23, 24, 25]);
    });
});
