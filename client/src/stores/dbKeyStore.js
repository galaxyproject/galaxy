import UploadUtils from "components/Upload/utils";
import { defineStore } from "pinia";

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
