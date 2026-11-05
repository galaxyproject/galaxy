import {
    computed,
    getCurrentScope,
    type MaybeRefOrGetter,
    onScopeDispose,
    readonly,
    ref,
    shallowRef,
    toValue,
    watch,
} from "vue";

import type { TableField } from "@/components/Common/GTable.types";
import {
    SELECTION_STATES,
    type SelectionItem,
    type SelectItemsProvider,
    type SelectItemsQuery,
} from "@/components/SelectionDialog/selectionTypes";
import { errorMessageAsString } from "@/utils/simple-error";

export interface UseSelectItemsOptions {
    /** Item fields searched when the provider returns all items at once; default: every field that holds displayed text. */
    filterKeys?: string[];
}

const PER_PAGE = 25;

/** Item fields without displayed text, left out of the local search like the dialog table does. */
const FILTER_IGNORED_FIELDS = ["entry", "selectionState", "updateTime"];

interface PathLevel {
    item: SelectionItem;
    /** Page the level was opened from, restored by `back()`. */
    page: number;
}

type SortFormatter = TableField["formatter"];

/** Same order as GTable's local sort: formatted values, missing values last in both directions. */
function compareItems(a: SelectionItem, b: SelectionItem, key: string, desc: boolean, formatter?: SortFormatter) {
    let aValue = (a as unknown as Record<string, unknown>)[key];
    let bValue = (b as unknown as Record<string, unknown>)[key];
    if (formatter) {
        aValue = formatter(aValue, key, a);
        bValue = formatter(bValue, key, b);
    }
    if (aValue == null && bValue == null) {
        return 0;
    }
    if (aValue == null) {
        return 1;
    }
    if (bValue == null) {
        return -1;
    }
    const comparison =
        typeof aValue === "number" && typeof bValue === "number"
            ? aValue - bValue
            : String(aValue).localeCompare(String(bValue));
    return desc ? -comparison : comparison;
}

/**
 * Headless state of a selection dialog: builds one explicit query (path, page, filter, sort) per change,
 * loads it through the provider with an AbortController, drops stale responses, and keeps the selection.
 * A provider that returns a `total` pages and filters server-side; without one, the items are paged,
 * filtered and sorted here.
 */
export function useSelectItems<Raw>(
    provider: MaybeRefOrGetter<SelectItemsProvider<Raw>>,
    options: UseSelectItemsOptions = {},
) {
    const perPage = ref(PER_PAGE);

    const currentPage = ref(1);
    const currentFilter = ref("");
    const sortBy = ref<string>();
    const sortDesc = ref(false);
    const sortFormatter = shallowRef<SortFormatter>();
    const levels = shallowRef<PathLevel[]>([]);

    const loadedItems = shallowRef<SelectionItem[]>([]);
    const serverTotal = ref<number>();
    const loaded = ref(false);
    const loading = ref(false);
    const error = ref("");
    const selected = shallowRef<SelectionItem[]>([]);

    let controller: AbortController | undefined;
    let requestId = 0;
    /** False until the current level answers, so changes before that cannot be served locally. */
    let pagingKnown = false;

    const path = computed(() => levels.value.map((level) => level.item));
    const serverPaging = computed(() => serverTotal.value !== undefined);
    const selectedIds = computed(() => new Set(selected.value.map((item) => item.id)));

    const localItems = computed(() => {
        let items = loadedItems.value;
        if (serverPaging.value) {
            return items;
        }
        const text = currentFilter.value.trim().toLowerCase();
        if (text) {
            items = items.filter((item) =>
                Object.entries(item).some(
                    ([key, value]) =>
                        value != null &&
                        (options.filterKeys
                            ? options.filterKeys.includes(key)
                            : !FILTER_IGNORED_FIELDS.includes(key)) &&
                        String(value).toLowerCase().includes(text),
                ),
            );
        }
        const key = sortBy.value;
        if (key) {
            items = [...items].sort((a, b) => compareItems(a, b, key, sortDesc.value, sortFormatter.value));
        }
        return items;
    });

    const total = computed(() => serverTotal.value ?? localItems.value.length);

    const items = computed<SelectionItem[]>(() => {
        let pageItems = localItems.value;
        if (!serverPaging.value) {
            const start = (currentPage.value - 1) * perPage.value;
            pageItems = pageItems.slice(start, start + perPage.value);
        }
        return pageItems.map((item) => {
            if (selectedIds.value.has(item.id)) {
                return { ...item, selectionState: SELECTION_STATES.SELECTED };
            }
            return item.isLeaf ? { ...item, selectionState: SELECTION_STATES.UNSELECTED } : item;
        });
    });

    async function load() {
        controller?.abort();
        const current = new AbortController();
        controller = current;
        const id = ++requestId;
        const source = toValue(provider);
        const query: SelectItemsQuery = {
            path: path.value,
            page: currentPage.value,
            perPage: perPage.value,
            filter: currentFilter.value,
            sortBy: sortBy.value,
            // unsorted levels keep the server's default direction
            sortDesc: sortBy.value ? sortDesc.value : undefined,
            signal: current.signal,
        };
        loading.value = true;
        try {
            const result = await source.load(query);
            if (id !== requestId) {
                return;
            }
            loadedItems.value = result.items.map((raw) => source.map(raw, query));
            serverTotal.value = result.total;
            pagingKnown = true;
            error.value = "";
            loaded.value = true;
        } catch (e) {
            // a newer query superseded (and aborted) this one
            if (id !== requestId) {
                return;
            }
            error.value = errorMessageAsString(e);
        } finally {
            if (id === requestId) {
                loading.value = false;
            }
        }
    }

    function loadIfServerPaged() {
        if (serverPaging.value || !pagingKnown) {
            void load();
        }
    }

    const page = computed({
        get: () => currentPage.value,
        set: (value: number) => {
            if (value !== currentPage.value) {
                currentPage.value = value;
                loadIfServerPaged();
            }
        },
    });

    const filter = computed({
        get: () => currentFilter.value,
        set: (text: string) => {
            if (text !== currentFilter.value) {
                currentFilter.value = text;
                currentPage.value = 1;
                loadIfServerPaged();
            }
        },
    });

    /** `formatter` is the sorted field's, so a local sort orders rows by their displayed text like GTable. */
    function setSort(key: string | undefined, desc = false, formatter?: SortFormatter) {
        sortBy.value = key || undefined;
        sortDesc.value = desc;
        sortFormatter.value = formatter;
        loadIfServerPaged();
    }

    /** Moves to another level: filter and sort are per level, so both reset. */
    function moveTo(nextLevels: PathLevel[], nextPage: number) {
        levels.value = nextLevels;
        pagingKnown = false;
        // the previous level's rows must not be clicked while the next one loads
        loadedItems.value = [];
        serverTotal.value = undefined;
        currentPage.value = nextPage;
        currentFilter.value = "";
        sortBy.value = undefined;
        sortDesc.value = false;
        sortFormatter.value = undefined;
        void load();
    }

    function open(item: SelectionItem) {
        if (loading.value && !pagingKnown) {
            return;
        }
        moveTo([...levels.value, { item, page: currentPage.value }], 1);
    }

    function back() {
        const popped = levels.value[levels.value.length - 1];
        if (popped) {
            moveTo(levels.value.slice(0, -1), popped.page);
        }
    }

    function toggle(item: SelectionItem) {
        if (!item.isLeaf) {
            return;
        }
        if (selectedIds.value.has(item.id)) {
            selected.value = selected.value.filter((entry) => entry.id !== item.id);
        } else {
            selected.value = [...selected.value, item];
        }
    }

    /** Checked adds the leaves of the current page; unchecked clears the whole selection. */
    function selectAll(checked: boolean) {
        if (checked) {
            const added = items.value.filter((item) => item.isLeaf && !selectedIds.value.has(item.id));
            selected.value = [...selected.value, ...added];
        } else {
            selected.value = [];
        }
    }

    function clearSelection() {
        selected.value = [];
    }

    watch(
        () => toValue(provider),
        () => moveTo([], 1),
    );

    if (getCurrentScope()) {
        onScopeDispose(() => {
            // invalidates the running request, so its abort is not reported as an error
            requestId++;
            controller?.abort();
        });
    }

    void load();

    return {
        back,
        clearSelection,
        error: readonly(error),
        filter,
        items,
        loaded: readonly(loaded),
        loading: readonly(loading),
        open,
        page,
        path,
        perPage: readonly(perPage),
        reload: load,
        selectAll,
        selected: computed(() => selected.value),
        serverPaging,
        setSort,
        sortBy: readonly(sortBy),
        sortDesc: readonly(sortDesc),
        toggle,
        total,
    };
}

export type SelectItemsState = ReturnType<typeof useSelectItems>;
