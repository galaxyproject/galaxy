export const state = {
    collectionAttributes: {},
    uploadDatatypes: [],
    uploadGenomes: [],
};
import Vue from "vue";
import { prependPath } from "utils/redirect";
import axios from "axios";
import UploadUtils from "mvc/upload/upload-utils";

const getters = {
    getCollectionAttributes: (state) => (collectionId) => {
        return state.collectionAttributes[collectionId] || null;
    },
    getUploadDatatypes: (state) => () => {
        return state.uploadDatatypes;
    },
    getUploadGenomes: (state) => () => {
        return state.uploadGenomes;
    },
};

const actions = {
    fetchCollectionAttributes: async ({ commit }, collectionId) => {
        const { data } = await axios.get(prependPath("api/dataset_collections/" + collectionId + "/attributes"));
        commit("saveCollectionAttributes", { collectionId, collectionAttributes: data });
    },
    fetchUploadDatatypes: async ({ commit }) => {
        await UploadUtils.getUploadDatatypes(true, UploadUtils.AUTO_EXTENSION)
            .then((data) => {
                commit("saveUploadDatatypes", { datatypes: data });
            })
            .catch((err) => {
                console.log("Error: unable to load datatypes", err);
            });
    },
    fetchUploadGenomes: async ({ commit }) => {
        await UploadUtils.getUploadGenomes(UploadUtils.DEFAULT_GENOME)
            .then((data) => {
                commit("saveUploadGenomes", { genomes: data });
            })
            .catch((err) => {
                console.log("Error: unable to load genomes", err);
            });
    },
};

const mutations = {
    saveCollectionAttributes: (state, { collectionId, collectionAttributes }) => {
        Vue.set(state.collectionAttributes, collectionId, collectionAttributes);
    },
    saveUploadDatatypes: (state, { datatypes }) => {
        state.uploadDatatypes = datatypes;
    },
    saveUploadGenomes: (state, { genomes }) => {
        state.uploadGenomes = genomes;
    },
};

export const collectionStore = {
    state,
    getters,
    actions,
    mutations,
};
