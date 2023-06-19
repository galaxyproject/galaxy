import { defineStore } from "pinia";
import Vue, { computed, ref } from "vue";
import type { components } from "@/schema";
import { sortByObjectProp } from "@/utils/sorting";
import { HistoryFilters } from "@/components/History/HistoryFilters";
import {
    cloneHistory,
    createAndSelectNewHistory,
    deleteHistoryById,
    getCurrentHistoryFromServer,
    getHistoryByIdFromServer,
    getHistoryCount,
    getHistoryList,
    secureHistoryOnServer,
    setCurrentHistoryOnServer,
    updateHistoryFields,
} from "@/stores/services/history.services";
import * as ArchiveServices from "@/stores/services/historyArchive.services";
import { useUserLocalStorage } from "@/composables/userLocalStorage";

export type HistorySummary = components["schemas"]["HistorySummary"];

const PAGINATION_LIMIT = 10;
const isLoadingHistory = new Set();

export const useHistoryStore = defineStore("historyStore", () => {
    const historiesLoading = ref(false);
    const historiesOffset = ref(0);
    const totalHistoryCount = ref(0);
    const pinnedHistories = useUserLocalStorage<{ id: string }[]>("history-store-pinned-histories", []);
    const storedCurrentHistoryId = ref<string | null>(null);
    const storedFilterTexts = ref<{ [key: string]: string }>({});
    const storedHistories = ref<{ [key: string]: HistorySummary }>({});

    const histories = computed(() => {
        return Object.values(storedHistories.value)
            .filter((h) => !h.archived)
            .sort(sortByObjectProp("name"));
    });

    const getFirstHistoryId = computed(() => {
        return histories.value[0]?.id ?? null;
    });

    const currentHistory = computed(() => {
        if (storedCurrentHistoryId.value !== null) {
            return getHistoryById.value(storedCurrentHistoryId.value);
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

    /** Returns history from storedHistories, will load history if not in store */
    const getHistoryById = computed(() => {
        return (historyId: string) => {
            if (!storedHistories.value[historyId]) {
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
        const currentHistory = await setCurrentHistoryOnServer(historyId);
        selectHistory(currentHistory as HistorySummary);
        setFilterText(historyId, "");
    }

    function setCurrentHistoryId(historyId: string) {
        storedCurrentHistoryId.value = historyId;
    }

    function setFilterText(historyId: string, filterText: string) {
        Vue.set(storedFilterTexts.value, historyId, filterText);
    }

    function setHistory(history: HistorySummary) {
        Vue.set(storedHistories.value, history.id, history);
    }

    function setHistories(histories: HistorySummary[]) {
        // The incoming history list may contain less information than the already stored
        // histories, so we ensure that already available details are not getting lost.
        const enrichedHistories = histories.map((history) => {
            const historyState = storedHistories.value[history.id] || {};
            return Object.assign({}, historyState, history);
        });
        // Histories are provided as list but stored as map.
        const newMap = enrichedHistories.reduce((acc, h) => ({ ...acc, [h.id]: h }), {}) as {
            [key: string]: HistorySummary;
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

    function unpinHistory(historyId: string) {
        pinnedHistories.value = pinnedHistories.value.filter((h) => h.id !== historyId);
    }

    function selectHistory(history: HistorySummary) {
        setHistory(history);
        setCurrentHistoryId(history.id);
    }

    async function applyFilters(historyId: string, filters: Record<string, string | boolean>) {
        if (currentHistoryId.value !== historyId) {
            await setCurrentHistory(historyId);
        }
        const filterText = HistoryFilters.getFilterText(HistoryFilters.getValidFilterSettings(filters));
        setFilterText(historyId, filterText);
    }

    async function copyHistory(history: HistorySummary, name: string, copyAll: boolean) {
        const newHistory = (await cloneHistory(history, name, copyAll)) as HistorySummary;
        await handleTotalCountChange(1);
        return setCurrentHistory(newHistory.id);
    }

    async function createNewHistory() {
        const newHistory = await createAndSelectNewHistory();
        await handleTotalCountChange(1);
        return selectHistory(newHistory as HistorySummary);
    }

    function getNextAvailableHistoryId(excludedIds: string[]) {
        const historyIds = Object.keys(storedHistories.value);
        const filteredHistoryIds = historyIds.filter((id) => !excludedIds.includes(id));
        return filteredHistoryIds[0];
    }

    async function deleteHistory(historyId: string, purge: boolean) {
        const deletedHistory = (await deleteHistoryById(historyId, purge)) as HistorySummary;
        const nextAvailableHistoryId = getNextAvailableHistoryId([deletedHistory.id]);
        if (nextAvailableHistoryId) {
            await setCurrentHistory(nextAvailableHistoryId);
        } else {
            await createNewHistory();
        }
        Vue.delete(storedHistories.value, deletedHistory.id);
        await handleTotalCountChange(1, true);
    }

    async function loadCurrentHistory() {
        const history = await getCurrentHistoryFromServer();
        selectHistory(history as HistorySummary);
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
        await getHistoryCount().then((count) => (totalHistoryCount.value = count));
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
            await getHistoryList(offset, limit, queryString)
                .then(async (histories) => {
                    setHistories(histories);
                    if (paginate && !queryString && historiesOffset.value == offset) {
                        await handleTotalCountChange(histories.length);
                    }
                })
                .catch((error) => console.warn(error))
                .finally(() => setHistoriesLoading(false));
        }
    }

    async function loadHistoryById(historyId: string) {
        if (!isLoadingHistory.has(historyId)) {
            isLoadingHistory.add(historyId);
            await getHistoryByIdFromServer(historyId)
                .then((history) => setHistory(history as HistorySummary))
                .catch((error: Error) => console.warn(error))
                .finally(() => {
                    isLoadingHistory.delete(historyId);
                });
        }
    }

    async function secureHistory(history: HistorySummary) {
        const securedHistory = await secureHistoryOnServer(history);
        setHistory(securedHistory as HistorySummary);
    }

    async function archiveHistoryById(historyId: string, archiveExportId?: string, purgeHistory = false) {
        const history = await ArchiveServices.archiveHistoryById(historyId, archiveExportId, purgeHistory);
        setHistory(history as HistorySummary);
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
        const history = await ArchiveServices.unarchiveHistoryById(historyId, force);
        setHistory(history as HistorySummary);
        return history;
    }

    async function updateHistory({ id, ...update }: HistorySummary) {
        const savedHistory = await updateHistoryFields(id, update);
        setHistory(savedHistory as HistorySummary);
    }

    return {
        histories,
        currentHistory,
        currentHistoryId,
        currentFilterText,
        pinnedHistories,
        getHistoryById,
        getHistoryNameById,
        setCurrentHistory,
        setCurrentHistoryId,
        setFilterText,
        setHistory,
        setHistories,
        pinHistory,
        unpinHistory,
        selectHistory,
        applyFilters,
        copyHistory,
        createNewHistory,
        deleteHistory,
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
    };
});
