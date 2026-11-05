import { defineStore } from "pinia";

import { getDatatypesMapper } from "@/components/Datatypes";
import type { DatatypesMapperModel } from "@/components/Datatypes/model";
import { rethrowSimple } from "@/utils/simple-error";

interface State {
    datatypesMapper: DatatypesMapperModel | null;
    loading: boolean;
}

// Shared by concurrent callers; a promise is not store state, so it lives here.
let pendingLoad: Promise<void> | null = null;

export const useDatatypesMapperStore = defineStore("datatypesMapperStore", {
    state: (): State => ({
        datatypesMapper: null,
        loading: false,
    }),
    actions: {
        async createMapper() {
            if (this.datatypesMapper) {
                return;
            }
            if (!pendingLoad) {
                this.loading = true;
                pendingLoad = (async () => {
                    try {
                        this.datatypesMapper = await getDatatypesMapper(false);
                    } catch (error) {
                        rethrowSimple(error);
                    } finally {
                        this.loading = false;
                        pendingLoad = null;
                    }
                })();
            }
            return pendingLoad;
        },
    },
});
