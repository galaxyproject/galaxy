import { LastQueue } from "utils/promise-queue";
import { urlData } from "utils/url";
import { mergeListing } from "./utilities";

const queue = new LastQueue();

const state = {
    items: [],
    itemKey: "element_index",
    itemQueryKey: null,
};

const getters = {
    getCollectionElements: (state) => () => {
        return state.items.filter((n) => n);
    },
};

const actions = {
    fetchCollectionElements: async ({ commit }, { contentsurl, offset, limit }) => {
        const url = `${contentsurl}?offset=${offset}&limit=${limit}`;
        queue.enqueue(urlData, { url }).then((payload) => {
            const newQueryKey = contentsurl;
            commit("saveCollectionElements", { newQueryKey, payload });
        });
    },
};

const mutations = {
    saveCollectionElements: (state, { payload, newQueryKey }) => {
        mergeListing(state, { payload, newQueryKey });
    },
};

export const collectionElementsStore = {
    state,
    getters,
    actions,
    mutations,
};
