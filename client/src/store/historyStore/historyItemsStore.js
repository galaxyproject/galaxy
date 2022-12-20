/**
 * Requests history items by reacting to changes of filter props passed
 * to the history items provider used in the history panel.
 */

import Vue from "vue";
import { reverse } from "lodash";
import { LastQueue } from "utils/promise-queue";
import { urlData } from "utils/url";
import { mergeArray } from "./model/utilities";
import { getFilters, getQueryString, testFilters } from "utils/filterConversion";

const limit = 100;
const queue = new LastQueue();

const state = {
    items: {},
    itemKey: "hid",
    latestCreateTime: new Date(),
    totalMatchesCount: undefined,
    lastCheckedTime: new Date(),
    matchedHids: {},
    isWatching: false,
};

const getters = {
    getHistoryItems:
        (state) =>
        ({ historyId, filterText }) => {
            const itemArray = state.items[historyId] || [];
            const filters = getFilters(filterText).filter((filter) => !filter.includes("related"));
            const filtered = itemArray.filter((item) => {
                if (!item) {
                    return false;
                }
                if (!testFilters(filters, item)) {
                    return false;
                }
                if (!state.matchedHids[historyId].includes(item.hid)) {
                    return false;
                }
                return true;
            });
            return reverse(filtered);
        },
    getLatestCreateTime: (state) => () => state.latestCreateTime,
    getTotalMatchesCount: (state) => () => state.totalMatchesCount,
    getLastCheckedTime: (state) => () => state.lastCheckedTime,
    getWatchingVisibility: (state) => () => state.isWatching,
};

const actions = {
    fetchHistoryItems: async ({ commit }, { historyId, filterText, offset }) => {
        const queryString = getQueryString(filterText);
        const params = `v=dev&order=hid&offset=${offset}&limit=${limit}`;
        const url = `/api/histories/${historyId}/contents?${params}&${queryString}`;
        const headers = { accept: "application/vnd.galaxy.history.contents.stats+json" };
        await queue.enqueue(urlData, { url, headers }, historyId).then((data) => {
            const stats = data.stats;
            commit("saveQueryStats", { stats });
            const payload = data.contents;
            commit("saveHistoryItems", { historyId, payload });
        });
    },
};

const mutations = {
    saveHistoryItems: (state, { historyId, payload }) => {
        // merges incoming payload into existing state
        mergeArray(historyId, payload, state.items, state.itemKey);
        const payloadHids = [];
        // keep track of latest create time for items
        payload.forEach((item) => {
            if (item.state == "ok") {
                const itemCreateTime = new Date(item.create_time);
                if (itemCreateTime > state.latestCreateTime) {
                    state.latestCreateTime = itemCreateTime;
                }
            }
            payloadHids.push(item.hid);
        });
        Vue.set(state.matchedHids, historyId, payloadHids);
    },
    setLastCheckedTime: (state, { checkForUpdate }) => {
        state.lastCheckedTime = checkForUpdate;
    },
    setWatchingVisibility: (state, { watchingVisibility }) => {
        state.isWatching = watchingVisibility;
    },
    saveQueryStats: (state, { stats }) => {
        state.totalMatchesCount = stats.total_matches;
    },
};

export const historyItemsStore = {
    state,
    getters,
    actions,
    mutations,
};
