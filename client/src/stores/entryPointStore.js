import { defineStore } from "pinia";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";
import axios from "axios";
import isEqual from "lodash.isequal";

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
            let hasChanged = this.entryPoints.length !== data.length ? true : false;
            if (this.entryPoints.length === 0) {
                this.entryPoints = data;
            } else {
                const newEntryPoints = [];
                for (const ep of data) {
                    const olderEntryPoint = this.entryPoints.filter((item) => item.id === ep.id)[0];
                    if (!hasChanged && !isEqual(olderEntryPoint, ep)) {
                        hasChanged = true;
                    }
                    newEntryPoints.push(mergeEntryPoints(olderEntryPoint, ep));
                }
                if (hasChanged) {
                    this.entryPoints = newEntryPoints;
                }
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
