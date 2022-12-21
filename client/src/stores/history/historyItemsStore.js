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
        latestCreateTime: new Date(),
        totalMatchesCount: undefined,
        lastCheckedTime: new Date(),
        relatedItems: {},
        isWatching: false,
    }),
    getters: {
        getHistoryItems: (state) => {
            return (historyId, filterText) => {
                const itemArray = state.items[historyId] || [];
                const filters = HistoryFilters.getFilters(filterText).filter((filter) => !filter.includes("related"));
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
        getLatestCreateTime: (state) => {
            return state.latestCreateTime;
        },
        getTotalMatchesCount: (state) => {
            return state.totalMatchesCount;
        },
        getLastCheckedTime: (state) => {
            return state.lastCheckedTime;
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
                // keep track of latest create time for items
                payload.forEach((item) => {
                    if (item.state == "ok") {
                        const itemCreateTime = new Date(item.create_time);
                        if (itemCreateTime > state.latestCreateTime) {
                            state.latestCreateTime = itemCreateTime;
                        }
                    }
                    if (relatedHid) {
                        const relationKey = `${historyId}-${relatedHid}-${item.hid}`;
                        Vue.set(state.relatedItems, relationKey, true);
                    }
                });
            });
        },
        setLastCheckedTime(checkForUpdate) {
            this.lastCheckedTime = checkForUpdate;
        },
        setWatchingVisibility(watchingVisibility) {
            this.isWatching = watchingVisibility;
        },
    },
});
