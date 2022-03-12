import { reverse } from "lodash";
import { LastQueue } from "utils/promise-queue";
import { urlData } from "utils/url";
import { mergeListing } from "./utilities";

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

const actions = {
    fetchHistoryItems: async ({ commit, dispatch }, { historyId, offset, limit, queryString }) => {
        dispatch("startHistoryChangedItems", { historyId: historyId });
        const params = `v=dev&order=hid&offset=${offset}&limit=${limit}&${queryString}`;
        const url = `api/histories/${historyId}/contents?${params}`;
        queue.enqueue(urlData, { url }).then((payload) => {
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
