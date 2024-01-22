import UploadUtils from "components/Upload/utils";
import { defineStore } from "pinia";

export const useDatatypeStore = defineStore("datatypeStore", {
    state: () => ({
        uploadDatatypes: [],
    }),
    getters: {
        getUploadDatatypes: (state) => {
            return state.uploadDatatypes;
        },
    },
    actions: {
        async fetchUploadDatatypes() {
            try {
                const data = await UploadUtils.getUploadDatatypes(false, UploadUtils.AUTO_EXTENSION);
                this.uploadDatatypes = data;
            } catch (err) {
                console.log("Error: unable to load datatypes", err);
            }
        },
    },
});
