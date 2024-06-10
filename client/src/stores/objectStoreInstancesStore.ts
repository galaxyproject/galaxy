import { defineStore } from "pinia";

import { fetcher } from "@/api/schema/fetcher";
import type { components } from "@/api/schema/schema";
import { errorMessageAsString } from "@/utils/simple-error";

const getObjectStoreInstances = fetcher.path("/api/object_store_instances").method("get").create();

type UserConcreteObjectStoreModel = components["schemas"]["UserConcreteObjectStoreModel"];

export const useObjectStoreInstancesStore = defineStore("objectStoreInstances", {
    state: () => ({
        instances: [] as UserConcreteObjectStoreModel[],
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
        async handleInit(instances: UserConcreteObjectStoreModel[]) {
            this.instances = instances;
            this.fetched = true;
            this.error = null;
        },
        async handleError(err: unknown) {
            this.error = errorMessageAsString(err);
        },
        async fetchInstances() {
            try {
                const { data: instances } = await getObjectStoreInstances({});
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
