import { defineStore } from "pinia";

import { type components, GalaxyApi } from "@/api";
import { errorMessageAsString } from "@/utils/simple-error";

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
            const { data: instances, error } = await GalaxyApi().GET("/api/object_store_instances");

            if (error) {
                this.handleError(error);
                return;
            }

            this.handleInit(instances);
        },
        async ensureTemplates() {
            if (!this.fetched || this.error != null) {
                await this.fetchInstances();
            }
        },
    },
});
