import { defineStore } from "pinia";
import UploadUtils from "mvc/upload/upload-utils";

export const useDbKeyStore = defineStore("dbKeyStore", {
    state: () => ({
        uploadDbKeys: [],
    }),
    getters: {
        getUploadDbKeys: (state) => {
            return state.uploadDbKeys;
        },
    },
    actions: {
        async fetchUploadDbKeys() {
            try {
                const data = await UploadUtils.getUploadDbKeys(UploadUtils.DEFAULT_DBKEY);
                this.uploadDbKeys = data;
            } catch (err) {
                console.log("Error: unable to load Database/Builds", err);
            }
        },
    },
});
