import { computed, type MaybeRefOrGetter, type Ref, toValue } from "vue";

import type Filtering from "@/utils/filtering";

/**
 * Splits a `FilterMenu` query into valid and invalid filters, and builds the cleaned query from the valid ones
 * @param filterClass The filters the query is checked against
 * @param filterText The query as typed
 * @param backendFormatted Build the cleaned query in backend format (converted values, default filters kept)
 */
export function useFilterTextValidation<T>(
    filterClass: MaybeRefOrGetter<Filtering<T> | undefined>,
    filterText: Ref<string>,
    backendFormatted = true,
) {
    const rawFilters = computed<Record<string, T>>(() =>
        Object.fromEntries(toValue(filterClass)?.getFiltersForText(filterText.value, true, false) || []),
    );
    const validFilters = computed(
        () => toValue(filterClass)?.getValidFilters(rawFilters.value, true).validFilters ?? {},
    );
    const invalidFilters = computed(
        () => toValue(filterClass)?.getValidFilters(rawFilters.value, true).invalidFilters ?? {},
    );
    const isSurroundedByQuotes = computed(() => /^["'].*["']$/.test(filterText.value));
    const hasInvalidFilters = computed(
        () => !isSurroundedByQuotes.value && Object.keys(invalidFilters.value).length > 0,
    );

    /**
     * The query without its invalid filters: quoted text loses its quotes, text without filters is kept as is
     */
    function validatedFilterText(): string {
        if (isSurroundedByQuotes.value) {
            return filterText.value.slice(1, -1);
        } else if (Object.keys(rawFilters.value).length === 0) {
            return filterText.value;
        }
        // the typed text keeps plain text and exact-match quoting as written
        return toValue(filterClass)?.getFilterText(validFilters.value, backendFormatted, filterText.value) || "";
    }

    return { rawFilters, validFilters, invalidFilters, isSurroundedByQuotes, hasInvalidFilters, validatedFilterText };
}
