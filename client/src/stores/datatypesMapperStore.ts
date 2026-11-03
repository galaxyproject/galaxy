import { defineStore } from "pinia";

import { getDatatypesMapper } from "@/components/Datatypes";
import type { DatatypesMapperModel } from "@/components/Datatypes/model";
import { rethrowSimple } from "@/utils/simple-error";

interface State {
    datatypesMapper: DatatypesMapperModel | null;
    loading: boolean;
    pending: Promise<void> | null;
}

export const useDatatypesMapperStore = defineStore("datatypesMapperStore", {
    state: (): State => ({
        datatypesMapper: null,
        loading: false,
        pending: null,
    }),
    actions: {
        async createMapper() {
            if (this.datatypesMapper) {
                return;
            }
            // Concurrent callers share the request so a failed load rejects for all of them.
            if (!this.pending) {
                this.loading = true;
                this.pending = (async () => {
                    try {
                        this.datatypesMapper = await getDatatypesMapper(false);
                    } catch (error) {
                        rethrowSimple(error);
                    } finally {
                        this.loading = false;
                        this.pending = null;
                    }
                })();
            }
            return this.pending;
        },
    },
});
