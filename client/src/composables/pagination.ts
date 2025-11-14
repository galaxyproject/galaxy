import { computed, type ComputedRef, type Ref, ref } from "vue";

/**
 * Options for configuring pagination
 */
export interface UsePaginationOptions {
    /** Number of items per page (default: 24) */
    itemsPerPage?: number;
}

/**
 * Return type for the usePagination composable
 */
export interface UsePaginationReturn<T> {
    /** Current page number (1-indexed) */
    currentPage: Ref<number>;
    /** Number of items per page */
    itemsPerPage: Ref<number>;
    /** Paginated subset of items for the current page */
    paginatedItems: ComputedRef<T[]>;
    /** Total number of items */
    totalItems: ComputedRef<number>;
    /** Whether pagination should be shown (total items > items per page) */
    showPagination: ComputedRef<boolean>;
    /** Handler for page change events */
    onPageChange: (page: number) => void;
    /** Reset to first page */
    resetPage: () => void;
}

/**
 * Composable for client-side pagination of items
 *
 * @example
 * ```typescript
 * const items = ref([...]);
 * const { paginatedItems, currentPage, showPagination, onPageChange } = usePagination(items);
 *
 * // In template:
 * <ItemCard v-for="item in paginatedItems" :key="item.id" :item="item" />
 * <BPagination v-if="showPagination" :value="currentPage" @change="onPageChange" />
 * ```
 *
 * @param items - Reactive array of items to paginate
 * @param options - Pagination configuration options
 * @returns Pagination state and controls
 */
export function usePagination<T>(
    items: Ref<T[]> | ComputedRef<T[]>,
    options: UsePaginationOptions = {},
): UsePaginationReturn<T> {
    const { itemsPerPage: initialItemsPerPage = 24 } = options;

    const currentPage = ref(1);
    const itemsPerPage = ref(initialItemsPerPage);

    const totalItems = computed(() => items.value.length);

    const paginatedItems = computed(() => {
        const offset = (currentPage.value - 1) * itemsPerPage.value;
        const start = Math.max(0, offset);
        const end = Math.min(items.value.length, offset + itemsPerPage.value);
        return items.value.slice(start, end);
    });

    const showPagination = computed(() => totalItems.value > itemsPerPage.value);

    function onPageChange(page: number) {
        currentPage.value = page;
    }

    function resetPage() {
        currentPage.value = 1;
    }

    return {
        currentPage,
        itemsPerPage,
        paginatedItems,
        totalItems,
        showPagination,
        onPageChange,
        resetPage,
    };
}
