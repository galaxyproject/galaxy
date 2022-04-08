/**
 * Requests history items by reacting to changes of filter props passed
 * to the history items provider used in the history panel.
 */

import { reverse } from "lodash";
import { LastQueue } from "utils/promise-queue";
import { urlData } from "utils/url";
import { getFilters, getQueryDict, testFilters } from "./historyItemsFiltering";
import { mergeArray } from "./utilities";

const limit = 100;
const queue = new LastQueue();

const state = {
    items: {},
    itemKey: "hid",
    totalMatchesCount: undefined,
    latestCreateTime: new Date(),
};

const getters = {
    getHistoryItems:
        (state) =>
        ({ historyId, filterText }) => {
            const itemArray = state.items[historyId] || [];
            const filters = getFilters(filterText);
            const filtered = itemArray.filter((item) => {
                if (!item) {
                    return false;
                }
                if (!testFilters(filters, item)) {
                    return false;
                }
                return true;
            });
            return reverse(filtered);
        },
    getTotalMatchesCount: (state) => () => {
        return state.totalMatchesCount;
    },
    getHistoryItemByHid:
        (state) =>
        ({ historyId, hid }) => {
            const itemArray = state.items[historyId] || [];
            for (const item of itemArray) {
                if (item && item.hid == hid) {
                    return item;
                }
            }
            console.debug("getHistoryItemByHid failed. Hid not found.", historyId, hid);
        },
    getLatestCreateTime: (state) => () => state.latestCreateTime,
};

const getQueryString = (filterText) => {
    const filterDict = getQueryDict(filterText);
    return Object.entries(filterDict)
        .map(([f, v]) => `q=${f}&qv=${v}`)
        .join("&");
};

const actions = {
    fetchHistoryItems: async ({ commit, dispatch }, { historyId, filterText, offset }) => {
        dispatch("startHistoryChangedItems", { historyId: historyId });
        const queryString = getQueryString(filterText);
        const params = `v=dev&order=hid&offset=${offset}&limit=${limit}`;
        const url = `api/histories/${historyId}/contents?${params}&${queryString}`;
        const headers = { accept: "application/vnd.galaxy.history.contents.stats+json" };
        await queue.enqueue(urlData, { url, headers }).then((data) => {
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

        // keep track of latest create time for items
        payload.forEach((item) => {
            if (item.state == "ok") {
                const itemCreateTime = new Date(item.create_time);
                if (itemCreateTime > state.latestCreateTime) {
                    state.latestCreateTime = itemCreateTime;
                }
            }
        });
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
