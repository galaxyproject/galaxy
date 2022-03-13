/**
 * Requests collection elements by reacting to changes of filter props passed
 * to the collection elements provider used in the collection panel.
 */

import { LastQueue } from "utils/promise-queue";
import { urlData } from "utils/url";
import { mergeListing } from "./utilities";

const limit = 100;
const queue = new LastQueue();

const state = {
    items: [],
    itemKey: "element_index",
};

const getters = {
    getCollectionElements: (state) => () => {
        return state.items.filter((n) => n);
    },
};

const actions = {
    fetchCollectionElements: async ({ commit }, { contentsUrl, offset }) => {
        const url = `${contentsUrl}?offset=${offset}&limit=${limit}`;
        await queue.enqueue(urlData, { url }).then((payload) => {
            commit("saveCollectionElements", { payload });
        });
    },
};

const mutations = {
    saveCollectionElements: (state, { payload }) => {
        mergeListing(state, { payload });
    },
};

export const collectionElementsStore = {
    state,
    getters,
    actions,
    mutations,
};
