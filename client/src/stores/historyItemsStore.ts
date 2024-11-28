/**
 * Fetches history items from the API and stores them by `historyId`.
 * A computed getter returns items for the given `historyId` and
 * `filterText`.
 */

import { reverse } from "lodash";
import { defineStore } from "pinia";
import { computed, ref, set } from "vue";

import { type HistoryItemSummary } from "@/api";
import { HistoryFilters } from "@/components/History/HistoryFilters";
import { mergeArray } from "@/store/historyStore/model/utilities";
import { ActionSkippedError, LastQueue } from "@/utils/lastQueue";
import { urlData } from "@/utils/url";

type ExtendedHistoryItem = HistoryItemSummary & { sub_items?: HistoryItemSummary[] };

const limit = 100;

type ExpectedReturn = { stats: { total_matches: number }; contents: HistoryItemSummary[] };
const queue = new LastQueue<typeof urlData>(1000, true);

export const useHistoryItemsStore = defineStore("historyItemsStore", () => {
    const items = ref<Record<string, ExtendedHistoryItem[]>>({});
    const itemKey = ref("hid");
    const totalMatchesCount = ref<number | undefined>(undefined);
    const lastCheckedTime = ref(new Date());
    const lastUpdateTime = ref(new Date());
    const relatedItems = ref<Record<string, boolean>>({});
    const isWatching = ref(false);

    const getHistoryItems = computed(() => {
        return (historyId: string, filterText: string) => {
            const itemArray = items.value[historyId] || [];
            const filters = HistoryFilters.getFiltersForText(filterText).filter(
                (filter: [string, string]) => !filter[0].includes("related")
            );
            const relatedHid = HistoryFilters.getFilterValue(filterText, "related");
            const filtered = itemArray.filter((item: ExtendedHistoryItem) => {
                if (!item) {
                    return false;
                }
                if (!HistoryFilters.testFilters(filters, item)) {
                    // filters don't pass on the item, but they might pass on any of its sub_items
                    if (
                        !item.sub_items ||
                        !item.sub_items.some((subItem) => HistoryFilters.testFilters(filters, subItem))
                    ) {
                        return false;
                    }
                }
                const relationKey = `${historyId}-${relatedHid}-${item.hid}`;
                if (relatedHid && !relatedItems.value[relationKey]) {
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
            const relatedHid = HistoryFilters.getFilterValue(filterText, "related");
            saveHistoryItems(historyId, payload, relatedHid);
        } catch (e) {
            if (!(e instanceof ActionSkippedError)) {
                throw e;
            }
        }
    }

    function saveHistoryItems(historyId: string, payload: HistoryItemSummary[], relatedHid = null) {
        // merges incoming payload into existing state
        mergeArray(historyId, payload, items.value, itemKey.value);
        // if related filter is included, set keys in state
        if (relatedHid) {
            payload.forEach((item: HistoryItemSummary) => {
                // current `item.hid` is related to item with hid = `relatedHid`
                const relationKey = `${historyId}-${relatedHid}-${item.hid}`;
                set(relatedItems.value, relationKey, true);
            });
        }
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
