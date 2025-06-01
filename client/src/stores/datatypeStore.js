import UploadUtils from "components/Upload/utils";
import { defineStore } from "pinia";

import { fetchDatatypeDetails } from "@/api/datatypes";

export const useDatatypeStore = defineStore("datatypeStore", {
    state: () => ({
        uploadDatatypes: [],
        datatypeDetails: {},
    }),
    getters: {
        getUploadDatatypes: (state) => {
            return state.uploadDatatypes;
        },
        getDatatypeDetails: (state) => (extension) => {
            return state.datatypeDetails[extension];
        },
        isDatatypeAutoDownload: (state) => (extension) => {
            const details = state.datatypeDetails[extension];
            return details?.display_behavior === "download";
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
        async fetchDatatypeDetails(extension) {
            // Return cached details if available
            if (this.datatypeDetails[extension]) {
                return this.datatypeDetails[extension];
            }

            try {
                const details = await fetchDatatypeDetails(extension);
                this.datatypeDetails[extension] = details;
                return details;
            } catch (err) {
                console.error(`Error: unable to load datatype details for ${extension}`, err);
                return null;
            }
        },
    },
});
