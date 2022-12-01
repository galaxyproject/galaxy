import { defineStore } from "pinia";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";
import axios from "axios";

export const useEntryPointStore = defineStore("entryPointStore", {
    state: () => ({
        entryPoints: [],
        interval: undefined,
    }),
    getters: {
        entryPointsForJob: (state) => {
            return (jobId) => state.entryPoints.filter((entryPoint) => entryPoint["job_id"] === jobId);
        },
    },
    actions: {
        ensurePollingEntryPoints() {
            if (this.interval === undefined) {
                this.fetchEntryPoints();
                this.interval = setInterval(() => {
                    this.fetchEntryPoints();
                }, 5000);
            }
        },
        stopPollingEntryPoints() {
            this.interval = clearInterval(this.interval);
        },
        async fetchEntryPoints() {
            const url = getAppRoot() + `api/entry_points`;
            const params = { running: true };
            axios
                .get(url, { params: params })
                .then((response) => {
                    this.updateEntryPoints(response.data);
                })
                .catch((e) => {
                    rethrowSimple(e);
                });
        },
        updateEntryPoints(data) {
            if (this.entryPoints.length === 0) {
                this.entryPoints = data;
            } else {
                const newEntryPoints = [];
                for (const ep of data) {
                    const older_ep = this.entryPoints.filter((y) => y.id === ep.id)[0];
                    newEntryPoints.push(mergeEntryPoints(older_ep, ep));
                }
                this.entryPoints = newEntryPoints;
            }
            function mergeEntryPoints(original, updated) {
                return { ...original, ...updated };
            }
        },
        removeEntryPoint(toolId) {
            const index = this.entryPoints.findIndex((ep) => {
                return ep.id === toolId ? true : false;
            });
            if (index >= 0) {
                this.entryPoints.splice(index, 1);
            }
        },
    },
});
