import { computed, onMounted, ref, watch } from "vue";

import type { FilterFileSourcesOptions, RemoteEntry } from "@/api/remoteFiles";
import { browseRemoteFiles, fetchFileSources } from "@/api/remoteFiles";
import type { BreadcrumbItem } from "@/components/Common";
import { Model } from "@/components/FilesDialog/model";
import { entryToSelectionItem, fileSourcePluginToItem, sortFileSources } from "@/components/FilesDialog/utilities";
import type { SelectionItem } from "@/components/SelectionDialog/selectionTypes";
import { useFileSources } from "@/composables/fileSources";
import { useUrlTracker } from "@/composables/urlTracker";
import { errorMessageAsString } from "@/utils/simple-error";

export type RemoteFileBrowserMode = "file" | "directory" | "any";

export interface UseRemoteFileBrowserOptions {
    /** Which type of entries can be selected. Defaults to "file". */
    mode?: RemoteFileBrowserMode;
    /** Whether multiple entries can be selected at once. Defaults to false. */
    multiple?: boolean;
    /** Filters which file sources are displayed in the browser. */
    filterOptions?: FilterFileSourcesOptions;
}

/**
 * Composable encapsulating all state and logic for browsing and selecting remote file source entries.
 *
 * Handles navigation (breadcrumbs, drill-down), data loading (with race-condition guard),
 * server-side and client-side pagination/search, and multi/single selection.
 *
 * @param options - Configuration options for the browser.
 */
export function useRemoteFileBrowser(options: UseRemoteFileBrowserOptions = {}) {
    const { mode = "file", multiple = false, filterOptions = {} } = options;

    const filesSources = useFileSources(filterOptions);
    const urlTracker = useUrlTracker<SelectionItem>();
    const selectionModel = ref<Model>(new Model({ multiple }));
    const selectionCount = ref(0);

    const browserItems = ref<SelectionItem[]>([]);
    const allFetchedItems = ref<SelectionItem[]>([]);
    const isBusy = ref(false);
    const errorMessage = ref<string | undefined>();
    const searchQuery = ref("");
    const currentPage = ref(1);
    const perPage = ref(25);
    const totalMatches = ref(0);

    /**
     * Monotonically increasing sequence id used to discard stale async responses.
     * Incremented on every `load()` call; callbacks check that the id still matches
     * before applying their results.
     */
    const loadSequenceId = ref(0);

    const currentFileSourceUri = computed(() => urlTracker.current.value?.url);

    const supportsServerPagination = computed(() => filesSources.supportsPagination(currentFileSourceUri.value));

    const supportsServerSearch = computed(() => filesSources.supportsSearch(currentFileSourceUri.value));

    const hasPagination = computed(() => {
        if (urlTracker.isAtRoot.value || isBusy.value) {
            return false;
        }
        const itemCount = supportsServerPagination.value ? totalMatches.value : allFetchedItems.value.length;
        return itemCount > perPage.value;
    });

    const breadcrumbs = computed<BreadcrumbItem[]>(() => {
        const crumbs: BreadcrumbItem[] = [{ title: "Sources", index: -1 }];
        urlTracker.navigationHistory.value.forEach((item, index) => {
            crumbs.push({ title: item.label, index });
        });
        return crumbs;
    });

    /**
     * The subset of currently displayed items that are selectable based on the configured `mode`.
     * For "file" mode: only leaf (file) items.
     * For "directory" mode: only non-leaf (directory) items.
     * For "any" mode: all items.
     */
    const selectableItemsOnCurrentPage = computed(() => {
        return browserItems.value.filter((item) => isItemSelectable(item));
    });

    const allSelectableSelected = computed(() => {
        // Reference selectionCount to ensure reactivity on selection changes
        selectionCount.value;
        const items = selectableItemsOnCurrentPage.value;
        return items.length > 0 && items.every((item) => isSelected(item));
    });

    const someSelectableSelected = computed(() => {
        // Reference selectionCount to ensure reactivity on selection changes
        selectionCount.value;
        const items = selectableItemsOnCurrentPage.value;
        const selectedCount = items.filter((item) => isSelected(item)).length;
        return selectedCount > 0 && selectedCount < items.length;
    });

    // ---- Internal helpers ----

    function isItemSelectable(item: SelectionItem): boolean {
        if (mode === "file") {
            return item.isLeaf;
        }
        if (mode === "directory") {
            return !item.isLeaf;
        }
        return true;
    }

    /**
     * Runs an async operation, ignoring results if a newer load has been triggered
     * in the meantime (race-condition guard).
     */
    async function executeIfLatest<T>(
        operation: () => Promise<T>,
        onSuccess: (data: T) => void,
        onError?: (error: unknown) => void,
    ): Promise<void> {
        const seq = loadSequenceId.value;
        isBusy.value = true;
        errorMessage.value = undefined;

        try {
            const result = await operation();
            if (seq === loadSequenceId.value) {
                onSuccess(result);
            }
        } catch (error) {
            if (seq === loadSequenceId.value) {
                if (onError) {
                    onError(error);
                } else {
                    errorMessage.value = errorMessageAsString(error);
                }
            }
        } finally {
            if (seq === loadSequenceId.value) {
                isBusy.value = false;
            }
        }
    }

    function filterItemsBySearch(items: SelectionItem[]): SelectionItem[] {
        if (!searchQuery.value) {
            return items;
        }
        const query = searchQuery.value.toLowerCase();
        return items.filter((item) => item.label.toLowerCase().includes(query));
    }

    function paginateItems(items: SelectionItem[]): SelectionItem[] {
        const start = (currentPage.value - 1) * perPage.value;
        return items.slice(start, start + perPage.value);
    }

    function updateClientSideView() {
        const filteredItems = filterItemsBySearch(allFetchedItems.value);
        browserItems.value = paginateItems(filteredItems);
        totalMatches.value = filteredItems.length;
    }

    async function loadFileSources() {
        await executeIfLatest(
            () => fetchFileSources(filterOptions),
            (sources) => {
                let items = sources.map(fileSourcePluginToItem);
                items = items.sort(sortFileSources);

                if (searchQuery.value) {
                    const query = searchQuery.value.toLowerCase();
                    items = items.filter((item) => item.label.toLowerCase().includes(query));
                }

                browserItems.value = items;
            },
        );
    }

    async function loadDirectory(uri: string) {
        const hasServerPagination = supportsServerPagination.value;
        const hasServerSearch = supportsServerSearch.value;

        const limit = hasServerPagination ? perPage.value : undefined;
        const offset = hasServerPagination ? (currentPage.value - 1) * perPage.value : undefined;
        const query = hasServerSearch ? searchQuery.value || undefined : undefined;

        await executeIfLatest(
            () => browseRemoteFiles(uri, false, false, limit, offset, query),
            (result) => {
                const allEntries = result.entries.map((e: RemoteEntry) => entryToSelectionItem(e));

                if (hasServerPagination) {
                    browserItems.value = allEntries;
                    totalMatches.value = result.totalMatches;
                } else {
                    allFetchedItems.value = allEntries;
                    updateClientSideView();
                }
            },
            (error) => {
                browserItems.value = [];
                allFetchedItems.value = [];
                totalMatches.value = 0;
                errorMessage.value = errorMessageAsString(error);
            },
        );
    }

    // ---- Public API ----

    /**
     * Triggers a data load for the current location.
     * Increments the sequence id so any in-flight older requests are discarded.
     */
    async function load() {
        loadSequenceId.value += 1;
        if (urlTracker.isAtRoot.value) {
            allFetchedItems.value = [];
            await loadFileSources();
        } else if (urlTracker.current.value) {
            await loadDirectory(urlTracker.current.value.url);
        }
    }

    /** Navigate into a directory or file source. */
    function open(item: SelectionItem) {
        urlTracker.forward(item);
        currentPage.value = 1;
        clearSearch();
        load();
    }

    /** Navigate to a specific breadcrumb level. Pass -1 to return to the root. */
    function navigateToBreadcrumb(index: number) {
        if (index === -1) {
            urlTracker.reset();
        } else {
            const targetDepth = index + 1;
            const currentDepth = urlTracker.navigationHistory.value.length;
            const stepsBack = currentDepth - targetDepth;
            for (let i = 0; i < stepsBack; i++) {
                urlTracker.backward();
            }
        }
        currentPage.value = 1;
        clearSearch();
        load();
    }

    /** Toggle selection of an item, respecting the configured `mode`. */
    function toggleSelection(item: SelectionItem) {
        if (isItemSelectable(item)) {
            selectionModel.value.add(item);
            selectionCount.value = selectionModel.value.count();
        }
    }

    /** Returns whether the given item is currently selected. */
    function isSelected(item: SelectionItem): boolean {
        return selectionModel.value.exists(item.id);
    }

    /**
     * Toggles selection of all selectable items on the current page.
     * If all are selected, deselects them all; otherwise selects all unselected ones.
     */
    function toggleSelectAll() {
        const items = selectableItemsOnCurrentPage.value;
        const allSelected = items.every((item) => isSelected(item));
        items.forEach((item) => {
            const needsToggle = allSelected ? isSelected(item) : !isSelected(item);
            if (needsToggle) {
                selectionModel.value.add(item);
            }
        });
        selectionCount.value = selectionModel.value.count();
    }

    /** Returns all currently selected items as an array. */
    function getSelectedItems(): SelectionItem[] {
        const result = selectionModel.value.finalize();
        return Array.isArray(result) ? result : [result];
    }

    /** Clears the current search query without triggering a reload. */
    function clearSearch() {
        searchQuery.value = "";
    }

    /** Updates the search query, triggering a reload or client-side filter as appropriate. */
    function updateSearchQuery(newQuery: string) {
        searchQuery.value = newQuery;
    }

    /** Clears the current selection state. */
    function resetSelection() {
        selectionModel.value = new Model({ multiple });
        selectionCount.value = 0;
    }

    /**
     * Resets the entire browser state back to the root level and triggers a fresh load.
     * Useful when re-opening a modal or clearing a previously completed browsing session.
     */
    function reset() {
        urlTracker.reset();
        resetSelection();
        allFetchedItems.value = [];
        browserItems.value = [];
        currentPage.value = 1;
        clearSearch();
        errorMessage.value = undefined;
        load();
    }

    // ---- Watchers ----

    watch(searchQuery, () => {
        currentPage.value = 1;
        if (urlTracker.isAtRoot.value || supportsServerSearch.value) {
            load();
        } else if (allFetchedItems.value.length > 0) {
            updateClientSideView();
        }
    });

    watch(currentPage, () => {
        if (urlTracker.isAtRoot.value) {
            return;
        }
        if (supportsServerPagination.value) {
            load();
        } else if (allFetchedItems.value.length > 0) {
            updateClientSideView();
        }
    });

    onMounted(() => {
        load();
    });

    return {
        // Navigation
        urlTracker,
        breadcrumbs,
        navigateToBreadcrumb,
        open,
        clearSearch,
        // Data
        browserItems,
        isBusy,
        errorMessage,
        currentPage,
        perPage,
        totalMatches,
        hasPagination,
        searchQuery,
        updateSearchQuery,
        // Selection
        selectionCount,
        isSelected,
        toggleSelection,
        selectableItemsOnCurrentPage,
        allSelectableSelected,
        someSelectableSelected,
        toggleSelectAll,
        getSelectedItems,
        resetSelection,
        // Lifecycle
        load,
        reset,
    };
}
