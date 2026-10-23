/**
 * Composable for sorting the staged items of an upload table.
 *
 * The upload request, collection elements and pairing are all built from the
 * items array, so sorting reorders that array instead of letting the table sort
 * a copy for display. Bind `tableSortProps` and `tableSortEvents` on GTable; this
 * turns off GTable's local sorting (and with it, its local filtering).
 */

import { computed, type Ref, ref, toRaw, watch } from "vue";

type SortValue = string | number | null | undefined;

/** Per-column accessors for columns whose sort value is not a field of the item. */
export type SortValueGetters<T> = Record<string, (item: T) => SortValue>;

const collator = new Intl.Collator();

function compareValues(a: SortValue, b: SortValue): number {
    if (a == null && b == null) {
        return 0;
    }
    if (a == null) {
        return 1;
    }
    if (b == null) {
        return -1;
    }
    if (typeof a === "number" && typeof b === "number") {
        return a - b;
    }
    return collator.compare(String(a), String(b));
}

/**
 * Sorts `items` by a table column.
 *
 * @param items - Staged upload items shown in the table
 * @param sortValueGetters - Optional accessors keyed by column; other columns sort by `item[key]`
 */
export function useUploadTableSorting<T extends object>(items: Ref<T[]>, sortValueGetters: SortValueGetters<T> = {}) {
    const sortBy = ref("");
    const sortDesc = ref(false);

    function sortValue(item: T, key: string): SortValue {
        const getter = sortValueGetters[key];
        return getter ? getter(item) : ((item as Record<string, unknown>)[key] as SortValue);
    }

    function applySort() {
        const key = sortBy.value;
        if (!key) {
            return;
        }
        const direction = sortDesc.value ? -1 : 1;
        // Compute each sort value once and sort outside the reactive proxy, then replace the array once.
        const keyed = toRaw(items.value).map((item) => ({ item, value: sortValue(item, key) }));
        keyed.sort((a, b) => direction * compareValues(a.value, b.value));
        items.value = keyed.map(({ item }) => item);
    }

    /** Handler for GTable's `sort-changed` event. */
    function onSortChanged(key: string, desc: boolean) {
        sortBy.value = key;
        sortDesc.value = desc;
        applySort();
    }

    // Keep newly added items in the order the table header shows.
    watch(
        () => items.value.length,
        (length, previousLength) => {
            if (length > previousLength) {
                applySort();
            }
        },
    );

    /** GTable props; `sortBy`/`sortDesc` let a remounted table show the order the items are in. */
    const tableSortProps = computed(() => ({
        localSorting: false,
        sortBy: sortBy.value,
        sortDesc: sortDesc.value,
    }));

    const tableSortEvents = { "sort-changed": onSortChanged };

    return { tableSortProps, tableSortEvents, onSortChanged };
}
