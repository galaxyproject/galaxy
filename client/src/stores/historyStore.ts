import { defineStore } from "pinia";
import { computed, del, ref, set, watch } from "vue";

import {
    type AnyHistory,
    GalaxyApi,
    type HistoryContentsStats,
    type HistoryDetailed,
    type HistoryDevDetailed,
    type HistorySortByLiteral,
    type HistorySummary,
    type HistorySummaryExtended,
} from "@/api";
import {
    type AnyHistoryEntry,
    getArchivedHistories,
    getPublishedHistories,
    getSharedHistories,
    type UpdateHistoryPayload,
} from "@/api/histories";
import type { ArchivedHistoryDetailed } from "@/api/histories.archived";
import { getGalaxyInstance } from "@/app";
import { HistoryFilters } from "@/components/History/HistoryFilters";
import { useResourceWatcher } from "@/composables/resourceWatcher";
import { useSSE } from "@/composables/useNotificationSSE";
import { useUserLocalStorage } from "@/composables/userLocalStorage";
import { useConfigStore } from "@/stores/configurationStore";
import { useHistoryItemsStore } from "@/stores/historyItemsStore";
import {
    createAndSelectNewHistory,
    getCurrentHistoryFromServer,
    getHistoryByIdFromServer,
    getHistoryList,
    secureHistoryOnServer,
    setCurrentHistoryOnServer,
    updateHistoryFields,
} from "@/stores/services/history.services";
import { isRetryableApiError, MAX_RETRIES, rethrowSimple } from "@/utils/simple-error";
import { sortByObjectProp } from "@/utils/sorting";
import {
    ACTIVE_POLLING_INTERVAL,
    INACTIVE_POLLING_INTERVAL,
    refreshHistoryFromPush as refreshHistoryFromPushSuppliedApp,
    watchHistory as watchHistorySuppliedApp,
} from "@/watch/watchHistory";

const PAGINATION_LIMIT = 10;
/**
 * In-flight single history loads, keyed by id. The promise (rather than a bare
 * "is loading" flag) is kept so a second caller awaits the running request
 * instead of returning before its result reached the cache.
 */
const historyPromises = new Map<string, Promise<void>>();
const retryCounts: { [key: string]: number } = {};
const CONTENT_STATS_KEYS = ["size", "contents_active", "update_time"] as const;

/** Default number of entries requested per history listing fetch. */
const HISTORY_LIST_LIMIT = 25;

/**
 * The cached history listings that are not the current user's own histories.
 *
 * Own histories are cached in `storedHistories` (see `loadHistories`), which
 * also backs the current-history selection. Shared, published and archived
 * listings are kept apart from it on purpose: they may contain histories owned
 * by other users, which must never become candidates for the current history.
 */
export type HistoryListVariant = "shared" | "published" | "archived";

/** Options for fetching one of the cached history listings. */
export interface FetchHistoryListOptions {
    /** Optional free-text search forwarded to the backend. */
    search?: string;
    /** Maximum number of entries to fetch. Defaults to `HISTORY_LIST_LIMIT`. */
    limit?: number;
    /** Offset of the first entry to fetch. Defaults to `0`. */
    offset?: number;
    /** Field to sort by on the backend. Defaults to `update_time`. */
    sortBy?: HistorySortByLiteral;
    /** Sort direction on the backend. Defaults to `true` (most recent first). */
    sortDesc?: boolean;
    /** Discard the cached ids of this variant instead of merging into them. */
    replace?: boolean;
    /** Merge summaries by id without recording this request as the canonical variant listing. */
    record?: boolean;
}

function emptyHistoryListIds(): Record<HistoryListVariant, string[]> {
    return { shared: [], published: [], archived: [] };
}

function historyListFlags(value: boolean): Record<HistoryListVariant, boolean> {
    return { shared: value, published: value, archived: value };
}

function historyListCounts(): Record<HistoryListVariant, number> {
    return { shared: 0, published: 0, archived: 0 };
}

function byUpdateTimeDesc(a: AnyHistoryEntry, b: AnyHistoryEntry) {
    return (b.update_time ?? "").localeCompare(a.update_time ?? "");
}

export const useHistoryStore = defineStore("historyStore", () => {
    const historiesLoading = ref(false);
    const historiesOffset = ref(0);
    const totalHistoryCount = ref(0);
    const pinnedHistories = useUserLocalStorage<{ id: string }[]>("history-store-pinned-histories", []);
    const storedCurrentHistoryId = ref<string | null>(null);
    const storedFilterTexts = ref<{ [key: string]: string }>({});
    const storedHistories = ref<{ [key: string]: AnyHistory }>({});
    const historyLoadErrors = ref<{ [key: string]: Error }>({});
    const changingCurrentHistory = ref(false);
    const knownHistorySizes = new Map<string, number>();
    /** Summaries of every listed history, keyed by id, shared by all variants. */
    const listedHistories = ref<{ [key: string]: AnyHistoryEntry }>({});
    /** Ordered (and deduplicated) history ids per cached listing. */
    const listedHistoryIds = ref<Record<HistoryListVariant, string[]>>(emptyHistoryListIds());
    const listedHistoriesLoading = ref<Record<HistoryListVariant, boolean>>(historyListFlags(false));
    const listedHistoriesLoaded = ref<Record<HistoryListVariant, boolean>>(historyListFlags(false));
    const listedHistoriesTotal = ref<Record<HistoryListVariant, number>>(historyListCounts());
    /** In-flight own-history loads, keyed by request (see `loadHistories`). */
    const loadHistoriesPromises = new Map<string, Promise<void>>();
    /** In-flight listing fetches, keyed by request (see `fetchHistoryList`). */
    const listPromises = new Map<string, Promise<AnyHistoryEntry[]>>();

    const histories = computed(() => {
        return Object.values(storedHistories.value)
            .filter((h) => !h.archived)
            .sort(sortByObjectProp("name"));
    });

    const getFirstHistoryId = computed(() => {
        return histories.value[0]?.id ?? null;
    });

    const currentHistory = computed<HistorySummaryExtended | null>(() => {
        if (storedCurrentHistoryId.value !== null) {
            return getHistoryById.value(storedCurrentHistoryId.value) as HistorySummaryExtended;
        }
        return null;
    });

    const currentHistoryId = computed(() => {
        if (storedCurrentHistoryId.value === null || !(storedCurrentHistoryId.value in storedHistories.value)) {
            return getFirstHistoryId.value;
        } else {
            return storedCurrentHistoryId.value;
        }
    });

    const currentFilterText = computed(() => {
        if (currentHistoryId.value) {
            return storedFilterTexts.value[currentHistoryId.value];
        } else {
            return "";
        }
    });

    const getHistoryLoadError = computed(() => {
        return (historyId: string) => {
            return historyLoadErrors.value[historyId] ?? null;
        };
    });

    /** Returns history from storedHistories, will load history if not in store by default.
     * If shouldFetchIfMissing is false, will return null if history is not in store.
     */
    const getHistoryById = computed(() => {
        return (historyId: string, shouldFetchIfMissing = true) => {
            if (!storedHistories.value[historyId] && shouldFetchIfMissing) {
                const existingError = historyLoadErrors.value[historyId];
                const canRetry =
                    existingError && isRetryableApiError(existingError) && (retryCounts[historyId] ?? 0) <= MAX_RETRIES;
                if (!existingError || canRetry) {
                    loadHistoryById(historyId);
                }
            }
            return storedHistories.value[historyId] ?? null;
        };
    });

    const getHistoryNameById = computed(() => {
        return (historyId: string) => {
            const history = getHistoryById.value(historyId);
            if (history) {
                return history.name;
            } else {
                return "...";
            }
        };
    });

    /**
     * Returns the cached entries of a history listing, most recently updated
     * first. The entries returned by `fetchHistoryList` keep the order the
     * backend replied with instead.
     */
    const getListedHistories = computed(() => {
        return (variant: HistoryListVariant): AnyHistoryEntry[] => {
            return listedHistoryIds.value[variant]
                .map((historyId) => listedHistories.value[historyId])
                .filter((history): history is AnyHistoryEntry => history !== undefined)
                .sort(byUpdateTimeDesc);
        };
    });

    const sharedHistories = computed(() => getListedHistories.value("shared"));
    const publishedHistories = computed(() => getListedHistories.value("published"));
    const archivedHistories = computed(() => getListedHistories.value("archived"));

    /** Whether a listing fetch is currently in flight for the given variant. */
    const isHistoryListLoading = computed(() => {
        return (variant: HistoryListVariant) => listedHistoriesLoading.value[variant];
    });

    /** Whether the given listing has been fetched at least once. */
    const hasLoadedHistoryList = computed(() => {
        return (variant: HistoryListVariant) => listedHistoriesLoaded.value[variant];
    });

    /** Total number of entries the backend reported for the given listing. */
    const getHistoryListTotal = computed(() => {
        return (variant: HistoryListVariant) => listedHistoriesTotal.value[variant];
    });

    async function setCurrentHistory(historyId: string) {
        if (!changingCurrentHistory.value) {
            try {
                changingCurrentHistory.value = true;
                const currentHistory = (await setCurrentHistoryOnServer(historyId)) as HistoryDevDetailed;
                selectHistory(currentHistory);
                setFilterText(historyId, "");
            } catch (error) {
                rethrowSimple(error);
            } finally {
                changingCurrentHistory.value = false;
            }
        }
    }

    function setCurrentHistoryId(historyId: string) {
        storedCurrentHistoryId.value = historyId;
    }

    function setFilterText(historyId: string, filterText: string) {
        set(storedFilterTexts.value, historyId, filterText);
    }

    function setHistory(history: AnyHistory | HistoryContentsStats) {
        if (storedHistories.value[history.id] !== undefined) {
            // Merge the incoming history with existing one to keep additional information
            Object.entries(history).forEach(([key, value]) => {
                set(storedHistories.value[history.id]!, key, value);
            });
        } else {
            set(storedHistories.value, history.id, history);
        }
    }

    function didHistorySizeChange(history: { id: string; size: number }) {
        const previousHistorySize = knownHistorySizes.get(history.id);
        knownHistorySizes.set(history.id, history.size);
        return previousHistorySize !== history.size;
    }

    function setHistories(histories: AnyHistory[]) {
        // The incoming history list may contain less information than the already stored
        // histories, so we ensure that already available details are not getting lost.
        const enrichedHistories = histories.map((history) => {
            const historyState = storedHistories.value[history.id] || {};
            return Object.assign({}, historyState, history);
        });
        // Histories are provided as list but stored as map.
        const newMap = enrichedHistories.reduce((acc, h) => ({ ...acc, [h.id]: h }), {}) as {
            [key: string]: AnyHistory;
        };
        // Ensure that already stored histories, which are not available in the incoming array,
        // are not lost. This happens e.g. with shared histories since they have different owners.
        Object.values(storedHistories.value).forEach((history) => {
            const historyId = history.id;
            if (!newMap[historyId]) {
                newMap[historyId] = history;
            }
        });
        // Update stored histories
        storedHistories.value = newMap;
    }

    function setHistoriesLoading(loading: boolean) {
        historiesLoading.value = loading;
    }

    function pinHistory(historyId: string) {
        if (pinnedHistories.value.findIndex((item) => item.id == historyId) == -1) {
            pinnedHistories.value.push({ id: historyId });
        }
    }

    function unpinHistories(historyIds: string[]) {
        pinnedHistories.value = pinnedHistories.value.filter((h) => !historyIds.includes(h.id));
    }

    function clearPinnedHistories() {
        pinnedHistories.value = [];
    }

    function selectHistory(history: HistorySummary) {
        setHistory(history);
        setCurrentHistoryId(history.id);
    }

    async function applyFilters(historyId: string, filters: Record<string, string | number | boolean>) {
        if (currentHistoryId.value !== historyId) {
            await setCurrentHistory(historyId);
        }
        const filterText = HistoryFilters.getFilterText(filters);
        setFilterText(historyId, filterText);
    }

    async function copyHistory(history: HistorySummary, name: string, copyAll: boolean) {
        const { data, error } = await GalaxyApi().POST("/api/histories", {
            params: { query: { view: "detailed" } },
            body: {
                name,
                all_datasets: copyAll,
                history_id: history.id,
                archive_type: undefined,
            },
        });

        if (error) {
            rethrowSimple(error);
        }

        const newHistory = data as HistoryDetailed;
        await handleTotalCountChange(1);
        return setCurrentHistory(newHistory.id);
    }

    async function createNewHistory() {
        const newHistory = (await createAndSelectNewHistory()) as HistoryDevDetailed;
        await handleTotalCountChange(1);
        return selectHistory(newHistory);
    }

    function getNextAvailableHistoryId(excludedIds: string[]) {
        const historyIds = Object.keys(storedHistories.value);
        const filteredHistoryIds = historyIds.filter((id) => !excludedIds.includes(id));
        return filteredHistoryIds[0];
    }

    async function setNextAvailableHistoryId(excludedIds: string[]) {
        if (currentHistoryId.value && excludedIds.includes(currentHistoryId.value)) {
            const nextAvailableHistoryId = getNextAvailableHistoryId(excludedIds);
            if (nextAvailableHistoryId) {
                await setCurrentHistory(nextAvailableHistoryId);
            } else {
                await createNewHistory();
            }
        }
    }

    async function deleteHistory(historyId: string, purge = false) {
        const { data, error } = await GalaxyApi().DELETE("/api/histories/{history_id}", {
            params: { path: { history_id: historyId }, query: { purge } },
        });

        if (error) {
            rethrowSimple(error);
        }

        const deletedHistory = data as AnyHistory;
        await setNextAvailableHistoryId([deletedHistory.id]);
        del(storedHistories.value, deletedHistory.id);
        await handleTotalCountChange(1, true);
    }

    async function deleteHistories(ids: string[], purge = false) {
        const { data, error } = await GalaxyApi().PUT("/api/histories/batch/delete", {
            body: { ids, purge },
        });

        if (error) {
            rethrowSimple(error);
        }

        const deletedHistories = data as AnyHistory[];
        const historyIds = deletedHistories.map((history) => history.id);
        await setNextAvailableHistoryId(historyIds);
        deletedHistories.forEach((history) => {
            del(storedHistories.value, history.id);
        });
        await handleTotalCountChange(deletedHistories.length, true);
    }

    async function restoreHistory(historyId: string) {
        const { data, error } = await GalaxyApi().POST("/api/histories/deleted/{history_id}/undelete", {
            params: { path: { history_id: historyId } },
        });

        if (error) {
            rethrowSimple(error);
        }

        const restoredHistory = data as AnyHistory;
        await handleTotalCountChange(1);
        setHistory(restoredHistory);
    }

    async function restoreHistories(ids: string[]) {
        const { data, error } = await GalaxyApi().PUT("/api/histories/batch/undelete", {
            body: { ids },
        });

        if (error) {
            rethrowSimple(error);
        }

        const restoredHistories = data as AnyHistory[];
        await handleTotalCountChange(restoredHistories.length);
        setHistories(restoredHistories);
    }

    async function loadCurrentHistory(since?: string): Promise<HistoryDevDetailed | undefined> {
        try {
            const history = (await getCurrentHistoryFromServer(since)) as HistoryDevDetailed;
            if (!history) {
                return; // There are no changes to the current history, nothing to set
            }
            selectHistory(history);
            return history;
        } catch (error) {
            rethrowSimple(error);
        }
    }

    async function loadCurrentHistoryId(): Promise<string | null> {
        if (!currentHistoryId.value) {
            await loadCurrentHistory();
        }
        return currentHistoryId.value;
    }

    /**
     * This function handles the cases where a history has been created
     * or removed (to set pagination offset and fetch updated history count)
     *
     * @param count How many histories have been added/removed
     * @param reduction Whether it is a reduction or addition (default)
     */
    async function handleTotalCountChange(count = 0, reduction = false) {
        const adjustment = !reduction ? count : -count;
        historiesOffset.value = Math.max(0, historiesOffset.value + adjustment);
        await loadTotalHistoryCount();
    }

    async function loadTotalHistoryCount() {
        const { data, error } = await GalaxyApi().GET("/api/histories/count");

        if (error) {
            rethrowSimple(error);
        }

        totalHistoryCount.value = data;
    }

    /** TODO:
     * - not handling filters with pagination for now
     *   "pausing" pagination at the existing offset if a filter exists
     */
    async function fetchHistories(paginate: boolean, queryString?: string) {
        setHistoriesLoading(true);
        let limit: number | null = null;
        if (!queryString || queryString == "") {
            if (paginate) {
                await loadTotalHistoryCount();
                if (historiesOffset.value >= totalHistoryCount.value) {
                    setHistoriesLoading(false);
                    return;
                }
                limit = PAGINATION_LIMIT;
            } else {
                historiesOffset.value = 0;
            }
        }
        const offset = queryString ? 0 : historiesOffset.value;
        try {
            const histories = (await getHistoryList(offset, limit, queryString)) as HistorySummary[];
            setHistories(histories);
            if (paginate && !queryString && historiesOffset.value == offset) {
                await handleTotalCountChange(histories.length);
            }
        } catch (error) {
            rethrowSimple(error);
        } finally {
            setHistoriesLoading(false);
        }
    }

    /**
     * Loads the current user's histories into `storedHistories`.
     *
     * Identical calls made while a load is still running share that request and
     * resolve with it, so a consumer which starts searching while the first
     * fetch is in flight (the command palette) sees the filled cache instead of
     * an empty one. A *different* load started meanwhile is still skipped: the
     * store fetches one own-history list at a time.
     */
    function loadHistories(paginate = true, queryString?: string): Promise<void> {
        const key = `${paginate}|${queryString ?? ""}`;
        const inFlight = loadHistoriesPromises.get(key);
        if (inFlight) {
            return inFlight;
        }
        if (historiesLoading.value) {
            return Promise.resolve();
        }
        const promise = fetchHistories(paginate, queryString).finally(() => {
            loadHistoriesPromises.delete(key);
        });
        loadHistoriesPromises.set(key, promise);
        return promise;
    }

    /** Merges fetched entries into the shared summary map without changing a variant listing. */
    function mergeListedHistories(histories: AnyHistoryEntry[]) {
        histories.forEach((history) => {
            const storedHistory = listedHistories.value[history.id];
            // Incoming summaries may carry fewer fields than what is already
            // cached (e.g. a search result after a detailed listing), so merge
            // instead of overwriting.
            set(listedHistories.value, history.id, storedHistory ? { ...storedHistory, ...history } : history);
        });
    }

    /** Records fetched entries in the ordered id list of a variant, keeping ids unique. */
    function setListedHistories(variant: HistoryListVariant, histories: AnyHistoryEntry[], replace = false) {
        mergeListedHistories(histories);
        const incomingIds = histories.map((history) => history.id);
        const mergedIds = replace ? incomingIds : [...listedHistoryIds.value[variant], ...incomingIds];
        listedHistoryIds.value[variant] = Array.from(new Set(mergedIds));
    }

    /**
     * Fetches one of the cached history listings and merges the result into the
     * store. Only the entries which are not cached yet are added; already known
     * histories are updated in place.
     *
     * @param variant Which listing to fetch
     * @param options Pagination, sorting and search options
     * @returns The fetched entries, in the order the backend returned them
     */
    function fetchHistoryList(
        variant: HistoryListVariant,
        options: FetchHistoryListOptions = {},
    ): Promise<AnyHistoryEntry[]> {
        const {
            search = "",
            limit = HISTORY_LIST_LIMIT,
            offset = 0,
            sortBy = "update_time",
            sortDesc = true,
            replace = false,
            record = true,
        } = options;
        const key = [variant, search, limit, offset, sortBy, sortDesc, replace, record].join("|");

        const pending = listPromises.get(key);
        if (pending) {
            return pending;
        }
        const promise = requestHistoryList(
            variant,
            { search, limit, offset, sortBy, sortDesc },
            replace,
            record,
        ).finally(() => {
            listPromises.delete(key);
        });
        listPromises.set(key, promise);
        return promise;
    }

    /** Runs one listing request; `fetchHistoryList` owns the deduplication. */
    async function requestHistoryList(
        variant: HistoryListVariant,
        requestOptions: {
            search: string;
            limit: number;
            offset: number;
            sortBy: HistorySortByLiteral;
            sortDesc: boolean;
        },
        replace: boolean,
        record: boolean,
    ): Promise<AnyHistoryEntry[]> {
        if (record) {
            listedHistoriesLoading.value[variant] = true;
        }
        try {
            let result: { data: AnyHistoryEntry[]; total: number };
            if (variant === "shared") {
                result = await getSharedHistories(requestOptions);
            } else if (variant === "published") {
                result = await getPublishedHistories(requestOptions);
            } else {
                result = await getArchivedHistories(requestOptions);
            }
            if (record) {
                setListedHistories(variant, result.data, replace);
                listedHistoriesTotal.value[variant] = result.total;
                listedHistoriesLoaded.value[variant] = true;
            } else {
                mergeListedHistories(result.data);
            }
            return result.data.map((history) => listedHistories.value[history.id] ?? history);
        } catch (error) {
            return rethrowSimple(error);
        } finally {
            if (record) {
                listedHistoriesLoading.value[variant] = false;
            }
        }
    }

    /**
     * Fetches a history listing only if it has not been fetched before, so that
     * consumers can hydrate a listing without hitting the backend repeatedly.
     *
     * An identical fetch already in progress is shared by `fetchHistoryList`;
     * one-off searches use a different request key and do not suppress canonical
     * hydration. Always records, so that the listing it returns is the one it
     * hydrated.
     *
     * @returns the whole cached listing, not just the entries this call fetched
     */
    async function ensureHistoryListLoaded(
        variant: HistoryListVariant,
        options: Omit<FetchHistoryListOptions, "record"> = {},
    ): Promise<AnyHistoryEntry[]> {
        if (listedHistoriesLoaded.value[variant]) {
            return getListedHistories.value(variant);
        }
        await fetchHistoryList(variant, { ...options, record: true });
        return getListedHistories.value(variant);
    }

    /** Drops the cached ids of a listing (the summaries themselves are kept). */
    function clearHistoryList(variant: HistoryListVariant) {
        listedHistoryIds.value[variant] = [];
        listedHistoriesLoaded.value[variant] = false;
        listedHistoriesTotal.value[variant] = 0;
    }

    function watchHistory() {
        const app = getGalaxyInstance();
        return watchHistorySuppliedApp(app);
    }

    // SSE-driven history updates: when we receive a history_update event,
    // immediately trigger a refresh of the current history
    const SSE_HISTORY_EVENT_TYPES = ["history_update"] as const;
    const { connect: sseHistoryConnect, disconnect: sseHistoryDisconnect } = useSSE(
        handleHistorySSEEvent,
        SSE_HISTORY_EVENT_TYPES,
    );
    let stopHistoryPolling: (() => void) | null = null;
    let stopIsWatchingWatcher: (() => void) | null = null;

    function handleHistorySSEEvent(event: MessageEvent) {
        try {
            const data = JSON.parse(event.data);
            const changedHistoryIds: string[] = data.history_ids ?? [];
            if (!changedHistoryIds.length) {
                return;
            }
            const currentId = currentHistoryId.value;
            if (currentId && changedHistoryIds.includes(currentId)) {
                // SSE is itself the signal that the history changed — force the
                // refresh so the update_time short-circuit in watchHistoryOnce
                // can't suppress the contents fetch.
                const app = getGalaxyInstance();
                refreshHistoryFromPushSuppliedApp(app).catch((err) =>
                    console.error("Error refreshing current history from SSE push:", err),
                );
            }
            // Also refresh other tracked histories (e.g. visible in the
            // multi-history view). Skip ids not in storedHistories — there's
            // no rendered panel for them, so refetching wastes a request.
            const itemsStore = useHistoryItemsStore();
            for (const id of changedHistoryIds) {
                if (id === currentId) {
                    continue;
                }
                if (!storedHistories.value[id]) {
                    continue;
                }
                const filterText = storedFilterTexts.value[id] ?? "";
                updateContentStats(id).catch((err) =>
                    console.error(`Error updating content stats for history ${id}:`, err),
                );
                itemsStore
                    .fetchHistoryItems(id, filterText, 0)
                    .catch((err) => console.error(`Error fetching items for history ${id}:`, err));
            }
        } catch (e) {
            console.error("Error handling history SSE event:", e);
        }
    }

    // Choose between SSE and polling based on the server config flag
    // `enable_sse_updates`. SSE success at the socket level is not a
    // reliable proxy: the `/api/events/stream` endpoint accepts connections
    // even when the HistoryAuditMonitor is disabled, so relying on the
    // EventSource `connected` state would silently stop polling without any
    // events ever arriving.
    //
    // `useResourceWatcher` is instantiated lazily because it registers a
    // `visibilitychange` listener that calls `startWatchingResourceIfNeeded`
    // every time the tab regains focus — in SSE mode that would re-start
    // polling we explicitly don't want.
    const isWatchingHistory = ref(false);
    let watchingInitialized = false;
    function startWatchingHistoryWithSSE() {
        if (watchingInitialized) {
            return;
        }
        watchingInitialized = true;

        const configStore = useConfigStore();
        const decide = () => {
            if (configStore.config?.enable_sse_updates) {
                // SSE delivers incremental updates only; the store still needs
                // a baseline fetch so the history panel isn't empty until the
                // first change arrives.
                watchHistory().catch((err) => console.warn("Initial history load failed", err));
                sseHistoryConnect();
            } else {
                // The resource watcher fires its handler once immediately and
                // then re-schedules on the polling interval, which covers the
                // initial load as well as ongoing updates.
                const { startWatchingResource, stopWatchingResource, isWatchingResource } = useResourceWatcher(
                    watchHistory,
                    {
                        shortPollingInterval: ACTIVE_POLLING_INTERVAL,
                        longPollingInterval: INACTIVE_POLLING_INTERVAL,
                    },
                );
                stopHistoryPolling = stopWatchingResource;
                stopIsWatchingWatcher = watch(isWatchingResource, (v) => (isWatchingHistory.value = v), {
                    immediate: true,
                });
                startWatchingResource();
            }
        };

        if (configStore.isLoaded) {
            decide();
        } else {
            const stop = watch(
                () => configStore.isLoaded,
                (loaded) => {
                    if (loaded) {
                        stop();
                        decide();
                    }
                },
            );
        }
    }

    async function loadHistoryById(historyId: string) {
        const inFlight = historyPromises.get(historyId);
        if (inFlight) {
            // Share the running request: callers that need the name right after
            // (the command palette's invocation rows) must not resolve before it.
            await inFlight;
            return;
        }
        const promise = (async () => {
            const result = await getHistoryByIdFromServer(historyId);
            if (result.error) {
                retryCounts[historyId] = (retryCounts[historyId] ?? 0) + 1;
                set(historyLoadErrors.value, historyId, result.error);
            } else {
                setHistory(result.data);
                del(historyLoadErrors.value, historyId);
                delete retryCounts[historyId];
            }
        })();
        historyPromises.set(historyId, promise);
        try {
            await promise;
        } finally {
            historyPromises.delete(historyId);
        }
    }

    async function secureHistory(history: HistorySummary): Promise<{ sharingStatusChanged: boolean }> {
        const { securedHistory, sharingStatusChanged } = await secureHistoryOnServer(history);
        setHistory(securedHistory);
        return {
            sharingStatusChanged,
        };
    }

    async function archiveHistoryById(historyId: string, archiveExportId?: string, purgeHistory = false) {
        const { data, error } = await GalaxyApi().POST("/api/histories/{history_id}/archive", {
            params: {
                path: { history_id: historyId },
            },
            body: {
                archive_export_id: archiveExportId,
                purge_history: purgeHistory,
            },
        });

        if (error) {
            rethrowSimple(error);
        }

        const history = data as ArchivedHistoryDetailed;
        setHistory(history);
        if (!history.archived) {
            return;
        }

        // If the current history is archived, we need to switch to another one as it is
        // no longer part of the active histories.
        const nextHistoryId = getNextAvailableHistoryId([historyId]);
        if (nextHistoryId) {
            return setCurrentHistory(nextHistoryId);
        } else {
            return createNewHistory();
        }
    }

    async function unarchiveHistoryById(historyId: string, force?: boolean) {
        const { data, error } = await GalaxyApi().PUT("/api/histories/{history_id}/archive/restore", {
            params: {
                path: { history_id: historyId },
                query: { force },
            },
        });

        if (error) {
            rethrowSimple(error);
        }

        const history = data as ArchivedHistoryDetailed;
        setHistory(history);
        return history;
    }

    async function updateHistory(id: string, update: UpdateHistoryPayload) {
        const savedHistory = (await updateHistoryFields(id, update)) as HistorySummaryExtended;
        setHistory(savedHistory);
    }

    async function updateContentStats(historyId: string) {
        const { data, error } = await GalaxyApi().GET("/api/histories/{history_id}", {
            params: {
                path: { history_id: historyId },
                query: { keys: CONTENT_STATS_KEYS.join(",") },
            },
        });

        if (error) {
            rethrowSimple(error);
        }

        const contentStats = { id: historyId, ...data } as HistoryContentsStats;
        setHistory(contentStats);
        return contentStats;
    }

    // Closes SSE and stops polling so the watcher can't emit a trailing
    // anonymous-cookie request that would overwrite the authenticated
    // ``galaxysession`` cookie set by the login/register response.
    function stopWatchingHistory() {
        sseHistoryDisconnect();
        if (stopHistoryPolling) {
            stopHistoryPolling();
            stopHistoryPolling = null;
        }
        if (stopIsWatchingWatcher) {
            stopIsWatchingWatcher();
            stopIsWatchingWatcher = null;
        }
        isWatchingHistory.value = false;
        watchingInitialized = false;
    }

    return {
        histories,
        changingCurrentHistory,
        currentHistory,
        currentHistoryId,
        currentFilterText,
        pinnedHistories,
        storedHistories,
        getHistoryById,
        getHistoryLoadError,
        getHistoryNameById,
        setCurrentHistory,
        setCurrentHistoryId,
        setFilterText,
        setHistory,
        didHistorySizeChange,
        setHistories,
        pinHistory,
        unpinHistories,
        clearPinnedHistories,
        selectHistory,
        applyFilters,
        copyHistory,
        createNewHistory,
        deleteHistory,
        deleteHistories,
        restoreHistory,
        restoreHistories,
        handleTotalCountChange,
        startWatchingHistory: startWatchingHistoryWithSSE,
        stopWatchingHistory,
        isWatchingHistory,
        loadCurrentHistory,
        loadCurrentHistoryId,
        loadHistories,
        loadHistoryById,
        listedHistories,
        listedHistoryIds,
        getListedHistories,
        sharedHistories,
        publishedHistories,
        archivedHistories,
        isHistoryListLoading,
        hasLoadedHistoryList,
        getHistoryListTotal,
        setListedHistories,
        fetchHistoryList,
        ensureHistoryListLoaded,
        clearHistoryList,
        secureHistory,
        updateHistory,
        archiveHistoryById,
        unarchiveHistoryById,
        historiesLoading,
        historiesOffset,
        totalHistoryCount,
        updateContentStats,
    };
});
