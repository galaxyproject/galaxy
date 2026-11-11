import { computed, type MaybeRefOrGetter, type Ref, ref, toValue } from "vue";

import type Filtering from "@/utils/filtering";

import type { FieldFilter, FilterOption } from "./configs/types";

/** A column that may offer a filter dropdown in its header */
export interface ColumnFilterField {
    key: string;
    /** Column title, shown on the column's chips */
    title: string | null;
    filter?: FieldFilter;
}

/** A picked column filter item, shown as a removable chip */
export interface ColumnFilterChip {
    title: string | null;
    filter: FieldFilter;
    option: FilterOption;
}

/**
 * Column filter dropdowns that pick items into repeated `key:<id>` terms of a grid's filter text
 */
export function useColumnFilters<T>(
    fields: MaybeRefOrGetter<ColumnFilterField[]>,
    filterClass: Filtering<T> | undefined,
    filterText: Ref<string>,
    rawFilters: Ref<Record<string, T>>,
    maxPicks?: MaybeRefOrGetter<number | undefined>,
) {
    // names of the items picked in column filter dropdowns, by filter key and id
    const columnFilterNames = ref<Record<string, Record<string, FilterOption>>>({});

    const hasColumnFilters = computed(() => toValue(fields).some((field) => field.filter));

    /**
     * Set or remove (`undefined` value) several filters in the filter text at once
     */
    function setFilters(filters: Record<string, string | string[] | undefined>) {
        if (!filterClass) {
            return;
        }
        // column filters hold `MultiTags` id lists, which `Filtering<T>` types as `T`
        const toRemove = Object.fromEntries(
            Object.entries(filters).filter(([, value]) => value === undefined),
        ) as Record<string, T>;
        const toSet = Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== undefined)) as Record<
            string,
            T
        >;
        let text = filterText.value;
        if (Object.keys(toRemove).length > 0) {
            text = filterClass.applyFiltersToText(toRemove, text, true);
        }
        if (Object.keys(toSet).length > 0) {
            text = filterClass.applyFiltersToText(toSet, text);
        }
        filterText.value = text;
    }

    /**
     * Items currently selected in a column filter, read from the repeated `key:<id>` filter terms
     */
    function columnFilterSelection(filter: FieldFilter): FilterOption[] {
        const ids: unknown = rawFilters.value[filter.key];
        if (!Array.isArray(ids)) {
            return [];
        }
        const known = columnFilterNames.value[filter.key] ?? {};
        return ids.map((id: string) => known[id] ?? { id, name: id });
    }

    const activeColumnFilters = computed<ColumnFilterChip[]>(() =>
        toValue(fields).flatMap((field) => {
            const filter = field.filter;
            if (!filter) {
                return [];
            }
            return columnFilterSelection(filter).map((option) => ({ title: field.title, filter, option }));
        }),
    );

    const reachedColumnFilterLimit = computed(() => {
        const limit = toValue(maxPicks);
        return limit !== undefined && activeColumnFilters.value.length >= limit ? limit : undefined;
    });

    function onColumnFilter(filter: FieldFilter, options: FilterOption[]) {
        columnFilterNames.value = {
            ...columnFilterNames.value,
            [filter.key]: {
                ...columnFilterNames.value[filter.key],
                ...Object.fromEntries(options.map((option) => [option.id, option])),
            },
        };
        const cleared = Object.fromEntries((filter.clears ?? []).map((key) => [key, undefined]));
        const value = options.length > 0 ? options.map((option) => option.id) : undefined;
        setFilters({ ...cleared, [filter.key]: value });
    }

    function removeColumnFilterOption(filter: FieldFilter, option: FilterOption) {
        onColumnFilter(
            filter,
            columnFilterSelection(filter).filter((selectedOption) => selectedOption.id !== option.id),
        );
    }

    return {
        hasColumnFilters,
        columnFilterSelection,
        activeColumnFilters,
        reachedColumnFilterLimit,
        onColumnFilter,
        removeColumnFilterOption,
    };
}
