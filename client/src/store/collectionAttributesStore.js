export const state = {
    collectionAttributes: {},
};
import Vue from "vue";
import { prependPath } from "utils/redirect";
import axios from "axios";

const getters = {
    getCollectionAttributes: (state) => (collectionId) => {
        return state.collectionAttributes[collectionId] || null;
    },
};

const actions = {
    fetchCollectionAttributes: async ({ commit }, collectionId) => {
        const { data } = await axios.get(prependPath("api/dataset_collections/" + collectionId + "/attributes"));
        commit("saveCollectionAttributes", { collectionId, collectionAttributes: data });
    },
};

const mutations = {
    saveCollectionAttributes: (state, { collectionId, collectionAttributes }) => {
        Vue.set(state.collectionAttributes, collectionId, collectionAttributes);
    },
};

export const collectionAttributesStore = {
    state,
    getters,
    actions,
    mutations,
};
