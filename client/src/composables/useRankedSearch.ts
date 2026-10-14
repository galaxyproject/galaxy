import { type MaybeRefOrGetter, toValue } from "@vueuse/core";
import { computed, ref } from "vue";

import { buildSearchIndex, type FilterField, rankSearchIndex } from "@/composables/filter/filterFunction";

/**
 * Search state for a select with `internal-search` disabled: wire `onSearchChange` to its
 * `search-change` event and pass `rankedItems` as its options. The search index is rebuilt
 * only when `items` or `fields` change.
 */
export function useRankedSearch<O extends object>(
    items: MaybeRefOrGetter<O[]>,
    fields: MaybeRefOrGetter<FilterField<O>[]>,
) {
    const searchQuery = ref("");
    const searchIndex = computed(() => buildSearchIndex(toValue(items), toValue(fields)));
    const rankedItems = computed(() =>
        searchQuery.value.trim() ? rankSearchIndex(searchIndex.value, searchQuery.value) : toValue(items),
    );

    function onSearchChange(query: string) {
        searchQuery.value = query;
    }

    return { rankedItems, onSearchChange };
}
