import { defineStore } from "pinia";

import axios from "axios";
import { getAppRoot } from "onload/loadConfig";

export const useJobKeyStore = defineStore("jobStore", {
    state: () => ({
        job: {},
    }),
    getters: {
        job: (state) => (jobId) => {
            return state.job[jobId];
        },
    },
    actions: {
        async fetchJob(jobId) {
            try {
                const { data } = await axios.get(`${getAppRoot()}api/jobs/${jobId}?full=true`);
                this.job = data;
            } catch (err) {
                console.log("Error: unable to load Database/Builds", err);
            }
        },
    },
});
