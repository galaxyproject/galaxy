import axios from "axios";
import isEqual from "lodash.isequal";
import { getAppRoot } from "onload/loadConfig";
import { defineStore } from "pinia";
import { rethrowSimple } from "utils/simple-error";

export const useEntryPointStore = defineStore("entryPointStore", {
    state: () => ({
        entryPoints: [],
        pollTimeout: undefined,
        timeout: undefined,
    }),
    getters: {
        entryPointsForJob: (state) => {
            return (jobId) => state.entryPoints.filter((entryPoint) => entryPoint["job_id"] === jobId);
        },
        entryPointsForHda: (state) => {
            return (hdaId) =>
                state.entryPoints.filter((entryPoint) => entryPoint["output_datasets_ids"].includes(hdaId));
        },
    },
    actions: {
        async ensurePollingEntryPoints(timeout = 10000) {
            this.timeout = timeout;
            await this.fetchEntryPoints();
            // Another call to ensurePollingEntryPoints() might change this.timeout while waiting for fetchEntryPoints()
            if (this.timeout === timeout) {
                this.pollTimeout = setTimeout(() => {
                    this.ensurePollingEntryPoints(this.timeout);
                }, this.timeout);
            }
        },
        stopPollingEntryPoints() {
            this.pollTimeout = clearTimeout(this.pollTimeout);
        },
        async fetchEntryPoints() {
            this.stopPollingEntryPoints();
            const url = getAppRoot() + `api/entry_points`;
            const params = { running: true };
            try {
                const response = await axios.get(url, { params: params });
                this.updateEntryPoints(response.data);
            } catch (e) {
                rethrowSimple(e);
            }
        },
        updateEntryPoints(data) {
            let hasChanged = this.entryPoints.length !== data.length ? true : false;
            if (this.entryPoints.length === 0) {
                if (hasChanged) {
                    this.entryPoints = data;
                }
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
