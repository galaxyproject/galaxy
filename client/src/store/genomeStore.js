export const state = {
    uploadGenomes: [],
};
import UploadUtils from "mvc/upload/upload-utils";

const getters = {
    getUploadGenomes: (state) => () => {
        return state.uploadGenomes;
    },
};

const actions = {
    fetchUploadGenomes: async ({ commit }) => {
        try {
            const data = await UploadUtils.getUploadGenomes(UploadUtils.DEFAULT_GENOME);
            commit("saveUploadGenomes", { genomes: data });
        } catch (err) {
            console.log("Error: unable to load genomes", err);
        }
    },
};

const mutations = {
    saveUploadGenomes: (state, { genomes }) => {
        state.uploadGenomes = genomes;
    },
};

export const genomeStore = {
    state,
    getters,
    actions,
    mutations,
};
