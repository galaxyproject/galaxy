import { reverse } from "lodash";
import { LastQueue } from "utils/promise-queue";
import { urlData } from "components/providers/UrlDataProvider";
import { mergeListing } from "./utilities";

const queue = new LastQueue();

const state = {
    items: [],
    itemKey: "hid",
    queryCurrent: null,
};

const getters = {
    getHistoryItems: (state) => () => {
        const filtered = state.items.filter((n) => n);
        return reverse(filtered);
    },
};

const actions = {
    fetchHistoryItems: async ({ commit }, incoming) => {
        const url = `api/histories/${incoming.historyId}/contents?v=dev&order=hid&offset=${incoming.offset}&limit=${incoming.limit}&${incoming.queryString}`;
        queue.enqueue(urlData, { url }).then((payload) => {
            const queryKey = `${incoming.historyId}&${incoming.queryString}`;
            commit("saveHistoryItems", { queryKey, payload });
        });
    },
};

const mutations = {
    saveHistoryItems: (state, { queryKey, payload }) => {
        mergeListing(state, { queryKey, payload });
    },
};

export const historyItemsStore = {
    state,
    getters,
    actions,
    mutations,
};
