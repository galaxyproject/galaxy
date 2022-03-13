/**
 * Requests history items by reacting to changes of filter props passed
 * to the history items provider used in the history panel.
 */

import { reverse } from "lodash";
import { LastQueue } from "utils/promise-queue";
import { urlData } from "utils/url";
import { mergeListing } from "./utilities";

const limit = 100;
const queue = new LastQueue();

const state = {
    items: [],
    itemKey: "hid",
    itemQueryKey: null,
};

const getters = {
    getHistoryItems: (state) => () => {
        // TODO: Requires client side filtering.
        const filtered = state.items.filter((n) => n);
        return reverse(filtered);
    },
};

const getQueryString = (showDeleted, showHidden) => {
    const deleted = showDeleted ? "True" : "False";
    const visible = showHidden ? "False" : "True";
    return `q=deleted&q=visible&qv=${deleted}&qv=${visible}`;
};

const actions = {
    fetchHistoryItems: async ({ commit, dispatch }, { historyId, offset, showDeleted, showHidden }) => {
        dispatch("startHistoryChangedItems", { historyId: historyId });
        const queryString = getQueryString(showDeleted, showHidden);
        const params = `v=dev&order=hid&offset=${offset}&limit=${limit}`;
        const url = `api/histories/${historyId}/contents?${params}&${queryString}`;
        await queue.enqueue(urlData, { url }).then((payload) => {
            const newQueryKey = `${historyId}-${queryString}`;
            commit("saveHistoryItems", { payload, newQueryKey });
        });
    },
};

const mutations = {
    saveHistoryItems: (state, { payload, newQueryKey }) => {
        mergeListing(state, { payload, newQueryKey });
    },
};

export const historyItemsStore = {
    state,
    getters,
    actions,
    mutations,
};
