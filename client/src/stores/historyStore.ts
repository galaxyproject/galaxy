import { defineStore } from "pinia";
import { computed, del, ref, set } from "vue";

import {
    type AnyHistory,
    type HistoryContentsStats,
    type HistoryDevDetailed,
    type HistorySummary,
    type HistorySummaryExtended,
} from "@/api";
import {
    deleteHistories as deleteHistoriesByIds,
    deleteHistory as deleteHistoryById,
    historyFetcher,
    undeleteHistories,
    undeleteHistory,
} from "@/api/histories";
import { archiveHistory, unarchiveHistory } from "@/api/histories.archived";
import { HistoryFilters } from "@/components/History/HistoryFilters";
import { useUserLocalStorage } from "@/composables/userLocalStorage";
import {
    cloneHistory,
    createAndSelectNewHistory,
    getCurrentHistoryFromServer,
    getHistoryByIdFromServer,
    getHistoryCount,
    getHistoryList,
    secureHistoryOnServer,
    setCurrentHistoryOnServer,
    updateHistoryFields,
} from "@/stores/services/history.services";
import { rethrowSimple } from "@/utils/simple-error";
import { sortByObjectProp } from "@/utils/sorting";

const PAGINATION_LIMIT = 10;
const isLoadingHistory = new Set();
const CONTENT_STATS_KEYS = ["size", "contents_active", "update_time"] as const;

export const useHistoryStore = defineStore("historyStore", () => {
    const historiesLoading = ref(false);
    const historiesOffset = ref(0);
    const totalHistoryCount = ref(0);
    const pinnedHistories = useUserLocalStorage<{ id: string }[]>("history-store-pinned-histories", []);
    const storedCurrentHistoryId = ref<string | null>(null);
    const storedFilterTexts = ref<{ [key: string]: string }>({});
    const storedHistories = ref<{ [key: string]: AnyHistory }>({});

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

    /** Returns history from storedHistories, will load history if not in store by default.
     * If shouldFetchIfMissing is false, will return null if history is not in store.
     */
    const getHistoryById = computed(() => {
        return (historyId: string, shouldFetchIfMissing = true) => {
            if (!storedHistories.value[historyId] && shouldFetchIfMissing) {
                // TODO: Try to remove this as it can cause computed side effects
                loadHistoryById(historyId);
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

    async function setCurrentHistory(historyId: string) {
        const currentHistory = (await setCurrentHistoryOnServer(historyId)) as HistoryDevDetailed;
        selectHistory(currentHistory);
        setFilterText(historyId, "");
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
        const newHistory = (await cloneHistory(history, name, copyAll)) as HistorySummary;
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
        try {
            const { data } = await deleteHistoryById({ history_id: historyId, purge });
            const deletedHistory = data as AnyHistory;
            await setNextAvailableHistoryId([deletedHistory.id]);
            del(storedHistories.value, deletedHistory.id);
            await handleTotalCountChange(1, true);
        } catch (error) {
            rethrowSimple(error);
        }
    }

    async function deleteHistories(ids: string[], purge = false) {
        try {
            const { data } = await deleteHistoriesByIds({ ids, purge });
            const deletedHistories = data as AnyHistory[];
            const historyIds = deletedHistories.map((x) => String(x.id));
            await setNextAvailableHistoryId(historyIds);
            deletedHistories.forEach((history) => {
                del(storedHistories.value, history.id);
            });
            await handleTotalCountChange(deletedHistories.length, true);
        } catch (error) {
            rethrowSimple(error);
        }
    }

    async function restoreHistory(historyId: string) {
        try {
            const { data } = await undeleteHistory({ history_id: historyId });
            const restoredHistory = data as AnyHistory;
            await handleTotalCountChange(1);
            setHistory(restoredHistory);
        } catch (error) {
            rethrowSimple(error);
        }
    }

    async function restoreHistories(ids: string[]) {
        try {
            const { data } = await undeleteHistories({ ids });
            const restoredHistories = data as AnyHistory[];
            await handleTotalCountChange(restoredHistories.length);
            setHistories(restoredHistories);
        } catch (error) {
            rethrowSimple(error);
        }
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

    /**
     * This function handles the cases where a history has been created
     * or removed (to set pagination offset and fetch updated history count)
     *
     * @param count How many histories have been added/removed
     * @param reduction Whether it is a reduction or addition (default)
     */
    async function handleTotalCountChange(count = 0, reduction = false) {
        historiesOffset.value += !reduction ? count : -count;
        await loadTotalHistoryCount();
    }

    async function loadTotalHistoryCount() {
        totalHistoryCount.value = await getHistoryCount();
    }

    /** TODO:
     * - not handling filters with pagination for now
     *   "pausing" pagination at the existing offset if a filter exists
     */
    async function loadHistories(paginate = true, queryString?: string) {
        if (!historiesLoading.value) {
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
    }

    async function loadHistoryById(historyId: string): Promise<HistorySummaryExtended | undefined> {
        if (!isLoadingHistory.has(historyId)) {
            isLoadingHistory.add(historyId);
            try {
                const history = (await getHistoryByIdFromServer(historyId)) as HistorySummaryExtended;
                setHistory(history);
                return history;
            } catch (error) {
                rethrowSimple(error);
            } finally {
                isLoadingHistory.delete(historyId);
            }
        }
    }

    async function secureHistory(history: HistorySummary) {
        const securedHistory = (await secureHistoryOnServer(history)) as HistorySummaryExtended;
        setHistory(securedHistory);
    }

    async function archiveHistoryById(historyId: string, archiveExportId?: string, purgeHistory = false) {
        const history = await archiveHistory(historyId, archiveExportId, purgeHistory);
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
        const history = await unarchiveHistory(historyId, force);
        setHistory(history);
        return history;
    }

    async function updateHistory({ id, ...update }: HistorySummary) {
        const savedHistory = (await updateHistoryFields(id, update)) as HistorySummaryExtended;
        setHistory(savedHistory);
    }

    async function updateContentStats(historyId: string) {
        try {
            const { data } = await historyFetcher({
                history_id: historyId,
                keys: CONTENT_STATS_KEYS.join(","),
            });
            const contentStats = { id: historyId, ...data } as HistoryContentsStats;
            setHistory(contentStats);
            return contentStats;
        } catch (error) {
            rethrowSimple(error);
        }
    }

    return {
        histories,
        currentHistory,
        currentHistoryId,
        currentFilterText,
        pinnedHistories,
        storedHistories,
        getHistoryById,
        getHistoryNameById,
        setCurrentHistory,
        setCurrentHistoryId,
        setFilterText,
        setHistory,
        setHistories,
        pinHistory,
        unpinHistories,
        selectHistory,
        applyFilters,
        copyHistory,
        createNewHistory,
        deleteHistory,
        deleteHistories,
        restoreHistory,
        restoreHistories,
        handleTotalCountChange,
        loadCurrentHistory,
        loadHistories,
        loadHistoryById,
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
