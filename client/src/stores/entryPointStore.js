import { defineStore } from "pinia";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";
import axios from "axios";

export const useEntryPointStore = defineStore("entryPointStore", {
    state: () => ({
        entryPoints: [],
        interval: null,
    }),
    getters: {
        getEntryPoints: (state) => {
            return state.entryPoints;
        },
    },
    actions: {
        startPollingEntryPoints() {
            this.fetchEntryPoints();
            this.interval = setInterval(() => {
                this.fetchEntryPoints();
            }, 5000);
        },
        stopPollingEntryPoints() {
            clearInterval(this.interval);
        },
        async fetchEntryPoints() {
            const url = getAppRoot() + `api/entry_points`;
            const params = {"running": true}
            axios
                .get(url, { params: params })
                .then((response) => {
                    // TODO $patch here the minimal partial state object
                    // only if needed to minimize reactivity response
                    this.entryPoints = response.data;
                })
                .catch((e) => {
                    rethrowSimple(e);
                });
        },

    },
});
