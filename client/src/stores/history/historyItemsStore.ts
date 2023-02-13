/**
 * Requests history items by reacting to changes of filter props passed
 * to the history items provider used in the history panel.
 */

import { defineStore } from "pinia";
import { ref, type Ref, set, reactive } from "vue";
import { LastQueue } from "@/utils/promise-queue";
import { urlData } from "@/utils/url";
import { HistoryFilters } from "@/components/History/HistoryFilters";

// TODO: stricter type
export type HistoryItem = {
    [key: string]: unknown;
};

interface HistoryItemWithStats {
    stats: {
        total_matches: number;
    };
    contents: HistoryItem[];
}

const limit = 100;
const queue = new LastQueue<typeof urlData, string>();
const itemKey = "hid";

export const useHistoryItemsStore = defineStore("historyItemsStore", () => {
    const items: Ref<Record<string, HistoryItem[]>> = ref({});
    const latestCreateTime = ref(new Date());
    const totalMatchesCount = ref(0);
    const lastCheckedTime = ref(new Date());
    const relatedItems: Ref<Record<string, boolean>> = ref({});
    const isWatching = ref(false);

    function getHistoryItems(historyId: string, filterText: string) {
        const itemArray = items.value[historyId] || [];
        const filters = HistoryFilters.getFilters(filterText).filter((filter: string) => !filter.includes("related"));
        const relatedHid = HistoryFilters.getFilterValue(filterText, "related");

        const filtered = itemArray.filter((item) => {
            if (!item) {
                return false;
            }

            if (!HistoryFilters.testFilters(filters, item)) {
                return false;
            }

            const relationKey = `${historyId}-${relatedHid}-${item.hid}`;

            if (relatedHid && !relatedItems.value[relationKey]) {
                return false;
            } else {
                return true;
            }
        });

        return filtered.reverse();
    }

    async function fetchHistoryItems(historyId: string, filterText: string, offset: number) {
        const queryString = HistoryFilters.getQueryString(filterText);
        const params = `v=dev&order=hid&offset=${offset}&limit=${limit}`;
        const url = `/api/histories/${historyId}/contents?${params}&${queryString}`;
        const headers = { accept: "application/vnd.galaxy.history.contents.stats+json" };

        await queue.enqueue(urlData, [{ url, headers }], historyId).then((data) => {
            const stats = (data as HistoryItemWithStats).stats;
            totalMatchesCount.value = stats.total_matches;

            const payload = (data as HistoryItemWithStats).contents;
            const relatedHid = HistoryFilters.getFilterValue(filterText, "related");
            saveHistoryItems(historyId, payload, relatedHid);
        });
    }

    function saveHistoryItems(historyId: string, payload: HistoryItem[], relatedHid = null) {
        // merges incoming payload into existing state
        if (!items.value[historyId]) {
            set(items.value, historyId, ref([]));
        }

        const itemArray = items.value[historyId];
        payload.forEach((item) => {
            const itemIndex = item[itemKey] as number;

            if (itemArray[itemIndex]) {
                const localItem = itemArray[itemIndex];

                if (localItem.id == item.id) {
                    Object.keys(localItem).forEach((key) => {
                        localItem[key] = item[key];
                    });
                }
            } else {
                set(itemArray, itemIndex, reactive(item));
            }
        });

        // keep track of latest create time for items
        payload.forEach((item) => {
            if (item.state === "ok") {
                const itemCreateTime = new Date(item.create_time as string);
                if (itemCreateTime > latestCreateTime.value) {
                    latestCreateTime.value = itemCreateTime;
                }
            }
            if (relatedHid) {
                const relationKey = `${historyId}-${relatedHid}-${item.hid}`;
                set(relatedItems.value, relationKey, ref(true));
            }
        });
    }

    return {
        items,
        itemKey,
        latestCreateTime,
        totalMatchesCount,
        lastCheckedTime,
        relatedItems,
        isWatching,
        getHistoryItems,
        fetchHistoryItems,
        saveHistoryItems,
    };
});
