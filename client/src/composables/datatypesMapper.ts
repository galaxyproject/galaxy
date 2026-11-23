import { type Ref, ref } from "vue";

import type { DatatypesMapperModel } from "@/components/Datatypes/model";
import { Toast } from "@/composables/toast";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";
import { errorMessageAsString } from "@/utils/simple-error";

// Concurrent callers share one load and receive the same error, so it is toasted once.
let lastToastedError: unknown = null;

export function toastDatatypesLoadError(error: unknown) {
    if (error !== lastToastedError) {
        lastToastedError = error;
        Toast.error(errorMessageAsString(error), "Unable to load datatypes");
    }
}

export function useDatatypesMapper() {
    const datatypesMapperLoading = ref(true);
    const datatypesMapper: Ref<DatatypesMapperModel | null> = ref(null);
    const datatypesMapperStore = useDatatypesMapperStore();
    const datatypes: Ref<string[]> = ref([]);

    async function getDatatypesMapper() {
        try {
            await datatypesMapperStore.createMapper();
        } catch (error) {
            toastDatatypesLoadError(error);
        }
        datatypesMapperLoading.value = datatypesMapperStore.loading;
        datatypesMapper.value = datatypesMapperStore.datatypesMapper;
        if (datatypesMapperStore.datatypesMapper) {
            datatypes.value = datatypesMapperStore.datatypesMapper.datatypes;
        }
    }

    getDatatypesMapper();

    return { datatypes, datatypesMapper, datatypesMapperLoading };
}
