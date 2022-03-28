/**
 * Requests history items by reacting to changes of filter props passed
 * to the history items provider used in the history panel.
 */

import { reverse } from "lodash";
import { LastQueue } from "utils/promise-queue";
import { urlData } from "utils/url";
import { mergeArray } from "./utilities";
import { getFilters, getQueryDict, testFilters } from "./historyItemsFiltering";

const limit = 100;
const queue = new LastQueue();

const state = {
    items: {},
    itemKey: "hid",
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
};

const getQueryString = (filterText) => {
    const filterDict = getQueryDict(filterText);
    const queryString = Object.entries(filterDict)
        .map(([f, v]) => {
            if (f == "deleted-eq" || f == "visible-eq") {
                const pythonBool = String(v).toLowerCase() == "true" ? "True" : "False";
                return `${f.substring(0, f.length - 3)}=${pythonBool}`;
            } else {
                return `q=${f}&qv=${v}`;
            }
        })
        .join("&");
    return queryString;
};

const actions = {
    fetchHistoryItems: async ({ commit, dispatch }, { historyId, offset, filterText }) => {
        dispatch("startHistoryChangedItems", { historyId: historyId });
        const queryString = getQueryString(filterText);
        const params = `v=dev&order=hid&offset=${offset}&limit=${limit}`;
        const url = `api/histories/${historyId}/contents?${params}&${queryString}`;
        await queue.enqueue(urlData, { url }).then((payload) => {
            commit("saveHistoryItems", { historyId, payload });
        });
    },
};

const mutations = {
    saveHistoryItems: (state, { historyId, payload }) => {
        mergeArray(historyId, payload, state.items, state.itemKey);
    },
};

export const historyItemsStore = {
    state,
    getters,
    actions,
    mutations,
};
