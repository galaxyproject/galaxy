import { defineStore } from "pinia";

import { fetcher } from "@/api/schema/fetcher";
import type { components } from "@/api/schema/schema";
import { errorMessageAsString } from "@/utils/simple-error";

const getFileSourceInstances = fetcher.path("/api/file_source_instances").method("get").create();

type UserFileSourceModel = components["schemas"]["UserFileSourceModel"];

export const useFileSourceInstancesStore = defineStore("fileSourceInstances", {
    state: () => ({
        instances: [] as UserFileSourceModel[],
        fetched: false,
        error: null as string | null,
    }),
    getters: {
        getInstances: (state) => {
            return state.instances;
        },
        loading: (state) => {
            return !state.fetched;
        },
        getInstance: (state) => {
            return (uuid: string) => state.instances.find((i) => i.uuid == uuid);
        },
    },
    actions: {
        async handleInit(instances: UserFileSourceModel[]) {
            this.instances = instances;
            this.fetched = true;
            this.error = null;
        },
        async handleError(err: unknown) {
            this.error = errorMessageAsString(err);
        },
        async fetchInstances() {
            try {
                const { data: instances } = await getFileSourceInstances({});
                this.handleInit(instances);
            } catch (err) {
                this.handleError(err);
            }
        },
        async ensureTemplates() {
            if (!this.fetched || this.error != null) {
                await this.fetchInstances();
            }
        },
    },
});
