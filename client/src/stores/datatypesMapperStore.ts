import { defineStore } from "pinia";

import { getDatatypesMapper } from "@/components/Datatypes";
import { type DatatypesMapperModel } from "@/components/Datatypes/model";
import { rethrowSimple } from "@/utils/simple-error";

interface State {
    datatypesMapper: DatatypesMapperModel | null;
    loading: boolean;
}

export const useDatatypesMapperStore = defineStore("datatypesMapperStore", {
    state: (): State => ({
        datatypesMapper: null,
        loading: false,
    }),
    actions: {
        async createMapper(this: State) {
            if (!this.loading && !this.datatypesMapper) {
                this.loading = true;
                try {
                    this.datatypesMapper = await getDatatypesMapper(false);
                    this.loading = false;
                } catch (error) {
                    this.loading = false;
                    rethrowSimple(error);
                }
            }
        },
    },
});
