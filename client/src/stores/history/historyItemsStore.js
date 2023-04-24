/**
 * Requests history items by reacting to changes of filter props passed
 * to the history items provider used in the history panel.
 */

import { defineStore } from "pinia";
import Vue from "vue";
import { reverse } from "lodash";
import { LastQueue } from "utils/promise-queue";
import { urlData } from "utils/url";
import { mergeArray } from "store/historyStore/model/utilities";
import { HistoryFilters } from "components/History/HistoryFilters";

const limit = 100;
const queue = new LastQueue();

export const useHistoryItemsStore = defineStore("historyItemsStore", {
    state: () => ({
        items: {},
        itemKey: "hid",
        totalMatchesCount: undefined,
        lastCheckedTime: new Date(),
        lastUpdateTime: new Date(),
        relatedItems: {},
        isWatching: false,
    }),
    getters: {
        getHistoryItems: (state) => {
            return (historyId, filterText) => {
                const itemArray = state.items[historyId] || [];
                const filters = HistoryFilters.getFilters(filterText).filter(
                    (filter) => !filter[0].includes("related")
                );
                const relatedHid = HistoryFilters.getFilterValue(filterText, "related");
                const filtered = itemArray.filter((item) => {
                    if (!item) {
                        return false;
                    }
                    if (!HistoryFilters.testFilters(filters, item)) {
                        return false;
                    }
                    const relationKey = `${historyId}-${relatedHid}-${item.hid}`;
                    if (relatedHid && !state.relatedItems[relationKey]) {
                        return false;
                    }
                    return true;
                });
                return reverse(filtered);
            };
        },
        getTotalMatchesCount: (state) => {
            return state.totalMatchesCount;
        },
        getLastCheckedTime: (state) => {
            return state.lastCheckedTime;
        },
        getLastUpdateTime: (state) => {
            return state.lastUpdateTime;
        },
        getWatchingVisibility: (state) => {
            return state.isWatching;
        },
    },
    actions: {
        async fetchHistoryItems(historyId, filterText, offset) {
            const queryString = HistoryFilters.getQueryString(filterText);
            const params = `v=dev&order=hid&offset=${offset}&limit=${limit}`;
            const url = `/api/histories/${historyId}/contents?${params}&${queryString}`;
            const headers = { accept: "application/vnd.galaxy.history.contents.stats+json" };
            await queue.enqueue(urlData, { url, headers }, historyId).then((data) => {
                const stats = data.stats;
                this.totalMatchesCount = stats.total_matches;
                const payload = data.contents;
                const relatedHid = HistoryFilters.getFilterValue(filterText, "related");
                this.saveHistoryItems(historyId, payload, relatedHid);
            });
        },
        // Setters
        saveHistoryItems(historyId, payload, relatedHid = null) {
            this.$patch((state) => {
                // merges incoming payload into existing state
                mergeArray(historyId, payload, state.items, state.itemKey);
                // if related filter is included, set keys in state
                if (relatedHid) {
                    payload.forEach((item) => {
                        const relationKey = `${historyId}-${relatedHid}-${item.hid}`;
                        Vue.set(state.relatedItems, relationKey, true);
                    });
                }
            });
        },
        setLastCheckedTime(checkForUpdate) {
            this.lastCheckedTime = checkForUpdate;
        },
        setLastUpdateTime(lastUpdateTime = new Date()) {
            this.lastUpdateTime = lastUpdateTime;
        },
        setWatchingVisibility(watchingVisibility) {
            this.isWatching = watchingVisibility;
        },
    },
});
