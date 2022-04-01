/**
 * Requests history items by reacting to changes of filter props passed
 * to the history items provider used in the history panel.
 */

import { reverse } from "lodash";
import { LastQueue } from "utils/promise-queue";
import { urlDataWithHeaders } from "utils/url";
import { getFilters, getQueryDict, testFilters } from "./historyItemsFiltering";
import { mergeArray } from "./utilities";

const limit = 100;
const queue = new LastQueue();

const state = {
    items: {},
    itemKey: "hid",
    totalMatchesCount: undefined,
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
};

const getQueryString = (filterText) => {
    const filterDict = getQueryDict(filterText);
    return Object.entries(filterDict)
        .map(([f, v]) => `q=${f}&qv=${v}`)
        .join("&");
};

const actions = {
    fetchHistoryItems: async ({ commit, dispatch }, { historyId, offset, filterText }) => {
        dispatch("startHistoryChangedItems", { historyId: historyId });
        const queryString = getQueryString(filterText);
        const queryStats = "&view=count";
        const params = `v=dev&order=hid&offset=${offset}&limit=${limit}`;
        const url = `api/histories/${historyId}/contents?${params}&${queryString}${queryStats}`;
        await queue.enqueue(urlDataWithHeaders, { url }).then((response) => {
            const headers = response.headers;
            commit("saveQueryStats", { headers });
            const payload = response.data;
            commit("saveHistoryItems", { historyId, payload });
        });
    },
};

const mutations = {
    saveHistoryItems: (state, { historyId, payload }) => {
        mergeArray(historyId, payload, state.items, state.itemKey);
    },
    saveQueryStats: (state, { headers }) => {
        const totalMatches = headers["total_matches"];
        state.totalMatchesCount = Number(totalMatches);
    },
};

export const historyItemsStore = {
    state,
    getters,
    actions,
    mutations,
};
