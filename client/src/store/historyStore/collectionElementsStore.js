/**
 * Requests collection elements by reacting to changes of props passed to the collection elements
 * provider used in the collection panel e.g. changes of the offset prop when scrolling. This store
 * attached to the changed history items store, but could also use the getter of the dataset store
 * instead, particularly after a collection store has been added if required.
 */

import Vue from "vue";
import { LastQueue } from "utils/promise-queue";
import { urlData } from "utils/url";
import { mergeArray } from "./model/utilities";

const limit = 100;
const queue = new LastQueue();

const getObjectId = (elementObject) => {
    return `${elementObject.model_class}-${elementObject.id}`;
};

const state = {
    items: {},
    itemKey: "element_index",
    objectIndex: {},
};

const getters = {
    getCollectionElements:
        (state) =>
        ({ id }) => {
            const itemArray = state.items[id] || [];
            const filtered = itemArray.filter((item) => !!item);
            return filtered.map((item) => {
                const objectId = getObjectId(item.object);
                const objectData = state.objectIndex[objectId];
                const objectResult = { ...item.object };
                if (objectData) {
                    Object.keys(objectResult).forEach((key) => {
                        objectResult[key] = objectData[key];
                    });
                }
                return { ...item, object: objectResult };
            });
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
        mergeArray(id, payload, state.items, state.itemKey);
    },
    saveCollectionObjects: (state, { payload }) => {
        payload.forEach((item) => {
            const objectId = getObjectId(item);
            Vue.set(state.objectIndex, objectId, item);
        });
    },
};

export const collectionElementsStore = {
    state,
    getters,
    actions,
    mutations,
};
