/**
 * Fetches history items from the API and stores them by `historyId`.
 * A computed getter returns items for the given `historyId` and
 * `filterText`.
 */

import { reverse } from "lodash";
import { defineStore } from "pinia";
import { computed, ref } from "vue";

import type { HistoryItemSummary } from "@/api";
import { HistoryFilters } from "@/components/History/HistoryFilters";
import { mergeArray } from "@/store/historyStore/model/utilities";
import { ActionSkippedError, LastQueue } from "@/utils/lastQueue";
import { urlData } from "@/utils/url";

const limit = 100;

type ExpectedReturn = { stats: { total_matches: number }; contents: HistoryItemSummary[] };
const queue = new LastQueue<typeof urlData>(1000, true);

export const useHistoryItemsStore = defineStore("historyItemsStore", () => {
    const items = ref<Record<string, HistoryItemSummary[]>>({});
    const itemKey = ref("hid");
    const totalMatchesCount = ref<number | undefined>(undefined);
    const lastCheckedTime = ref(new Date());
    const lastUpdateTime = ref(new Date());
    const isWatching = ref(false);

    const getHistoryItems = computed(() => {
        return (historyId: string, filterText: string) => {
            const itemArray = items.value[historyId] || [];
            const filters = HistoryFilters.getFiltersForText(filterText);
            const filtered = itemArray.filter((item: HistoryItemSummary) => {
                if (!item) {
                    return false;
                }
                if (!HistoryFilters.testFilters(filters, item)) {
                    return false;
                }
                return true;
            });
            return reverse(filtered);
        };
    });

    async function fetchHistoryItems(historyId: string, filterText: string, offset: number) {
        const queryString = HistoryFilters.getQueryString(filterText);
        const params = `v=dev&order=hid&offset=${offset}&limit=${limit}`;
        const url = `/api/histories/${historyId}/contents?${params}&${queryString}`;
        const headers = { accept: "application/vnd.galaxy.history.contents.stats+json" };

        try {
            const data = await queue.enqueue(urlData, { url, headers, errorSimplify: false }, historyId);
            const stats = (data as ExpectedReturn).stats;
            totalMatchesCount.value = stats.total_matches;
            const payload = (data as ExpectedReturn).contents;

            /** filters that are not keys in history items **/
            const nonKeyedFilterValues: Record<string, string | null> = { related: null, invocation_id: null };
            for (const key of Object.keys(nonKeyedFilterValues)) {
                const filterValue = HistoryFilters.getFilterValue(filterText, key);
                if (filterValue) {
                    nonKeyedFilterValues[key] = filterValue;
                }
            }

            saveHistoryItems(historyId, payload, nonKeyedFilterValues);
        } catch (e) {
            if (!(e instanceof ActionSkippedError)) {
                throw e;
            }
        }
    }

    function saveHistoryItems(
        historyId: string,
        payload: HistoryItemSummary[],
        nonKeyedFilterValues: Record<string, string | null>
    ) {
        // merges incoming payload into existing state
        mergeArray(historyId, payload, items.value, itemKey.value, nonKeyedFilterValues);
    }

    function setLastUpdateTime(lastUpdated = new Date()) {
        lastUpdateTime.value = lastUpdated;
    }

    return {
        totalMatchesCount,
        lastCheckedTime,
        lastUpdateTime,
        isWatching,
        getHistoryItems,
        fetchHistoryItems,
        saveHistoryItems,
        setLastUpdateTime,
    };
});
