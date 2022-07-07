export const state = {
    uploadDbKeys: [],
};
import UploadUtils from "mvc/upload/upload-utils";

const getters = {
    getUploadDbKeys: (state) => () => {
        return state.uploadDbKeys;
    },
};

const actions = {
    fetchUploadDbKeys: async ({ commit }) => {
        try {
            const data = await UploadUtils.getUploadDbKeys(UploadUtils.DEFAULT_DBKEY);
            commit("saveUploadDbKeys", { dbKeys: data });
        } catch (err) {
            console.log("Error: unable to load Database/Builds", err);
        }
    },
};

const mutations = {
    saveUploadDbKeys: (state, { dbKeys }) => {
        state.uploadDbKeys = dbKeys;
    },
};

export const dbKeyStore = {
    state,
    getters,
    actions,
    mutations,
};
