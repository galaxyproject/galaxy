import { computed, ref } from "vue";

import { usePagination } from "./pagination";

describe("usePagination", () => {
    it("should paginate items with default settings", () => {
        const items = ref([1, 2, 3, 4, 5]);
        const { paginatedItems, currentPage, itemsPerPage } = usePagination(items);

        expect(currentPage.value).toBe(1);
        expect(itemsPerPage.value).toBe(24);
        expect(paginatedItems.value).toEqual([1, 2, 3, 4, 5]);
    });

    it("should paginate items correctly across multiple pages", () => {
        const items = ref(Array.from({ length: 50 }, (_, i) => i + 1));
        const { paginatedItems, currentPage, onPageChange } = usePagination(items, { itemsPerPage: 10 });

        expect(paginatedItems.value).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);

        onPageChange(2);
        expect(currentPage.value).toBe(2);
        expect(paginatedItems.value).toEqual([11, 12, 13, 14, 15, 16, 17, 18, 19, 20]);

        onPageChange(5);
        expect(currentPage.value).toBe(5);
        expect(paginatedItems.value).toEqual([41, 42, 43, 44, 45, 46, 47, 48, 49, 50]);
    });

    it("should show pagination only when items exceed page size", () => {
        const items = ref([1, 2, 3]);
        const { showPagination } = usePagination(items, { itemsPerPage: 5 });

        expect(showPagination.value).toBe(false);

        items.value = Array.from({ length: 10 }, (_, i) => i + 1);
        expect(showPagination.value).toBe(true);
    });

    it("should reset to first page", () => {
        const items = ref(Array.from({ length: 30 }, (_, i) => i + 1));
        const { currentPage, onPageChange, resetPage } = usePagination(items, { itemsPerPage: 10 });

        onPageChange(3);
        expect(currentPage.value).toBe(3);

        resetPage();
        expect(currentPage.value).toBe(1);
    });

    it("should compute total items correctly", () => {
        const items = ref([1, 2, 3]);
        const { totalItems } = usePagination(items);

        expect(totalItems.value).toBe(3);

        items.value = [...items.value, 4, 5];
        expect(totalItems.value).toBe(5);
    });

    it("should work with computed items", () => {
        const baseItems = ref([1, 2, 3, 4, 5, 6]);
        const filteredItems = computed(() => baseItems.value.filter((item) => item > 3));
        const { paginatedItems, totalItems } = usePagination(filteredItems, { itemsPerPage: 2 });

        expect(totalItems.value).toBe(3);
        expect(paginatedItems.value).toEqual([4, 5]);
    });

    it("should handle empty items array", () => {
        const items = ref<number[]>([]);
        const { paginatedItems, totalItems, showPagination } = usePagination(items);

        expect(paginatedItems.value).toEqual([]);
        expect(totalItems.value).toBe(0);
        expect(showPagination.value).toBe(false);
    });

    it("should handle last page with fewer items", () => {
        const items = ref(Array.from({ length: 25 }, (_, i) => i + 1));
        const { paginatedItems, onPageChange } = usePagination(items, { itemsPerPage: 10 });

        onPageChange(3);
        expect(paginatedItems.value).toEqual([21, 22, 23, 24, 25]);
    });
});
