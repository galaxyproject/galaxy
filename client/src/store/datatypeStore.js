export const state = {
    uploadDatatypes: [],
};
import UploadUtils from "mvc/upload/upload-utils";

const getters = {
    getUploadDatatypes: (state) => () => {
        return state.uploadDatatypes;
    },
};

const actions = {
    fetchUploadDatatypes: async ({ commit }) => {
        try {
            const data = await UploadUtils.getUploadDatatypes(false, UploadUtils.AUTO_EXTENSION);
            commit("saveUploadDatatypes", { datatypes: data });
        } catch (err) {
            console.log("Error: unable to load datatypes", err);
        }
    },
};

const mutations = {
    saveUploadDatatypes: (state, { datatypes }) => {
        state.uploadDatatypes = datatypes;
    },
};

export const datatypeStore = {
    state,
    getters,
    actions,
    mutations,
};
