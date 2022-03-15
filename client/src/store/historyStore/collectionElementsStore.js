/**
 * Requests collection elements by reacting to changes of filter props passed
 * to the collection elements provider used in the collection panel.
 */

import { LastQueue } from "utils/promise-queue";
import { urlData } from "utils/url";
import { mergeArray } from "./utilities";

const limit = 100;
const queue = new LastQueue();

const state = {
    items: {},
    itemKey: "element_index",
};

const getters = {
    getCollectionElements:
        (state) =>
        ({ id }) => {
            const itemArray = state.items[id] || [];
            const filtered = itemArray.filter((item) => {
                if (!item) {
                    return false;
                }
                return true;
            });
            return filtered;
        },
};

const actions = {
    fetchCollectionElements: async ({ commit }, { id, contentsUrl, offset }) => {
        const url = `${contentsUrl}?offset=${offset}&limit=${limit}`;
        await queue.enqueue(urlData, { url }).then((payload) => {
            commit("saveCollectionElements", { id, payload });
        });
    },
};

const mutations = {
    saveCollectionElements: (state, { id, payload }) => {
        mergeArray(id, state.items, state.itemKey, payload);
    },
};

export const collectionElementsStore = {
    state,
    getters,
    actions,
    mutations,
};
