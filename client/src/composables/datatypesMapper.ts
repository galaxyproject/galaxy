import { ref } from "vue";

import type { Ref } from "vue";

import type { DatatypesMapperModel } from "@/components/Datatypes/model";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";

export function useDatatypesMapper() {
    const datatypesMapperLoading = ref(true);
    const datatypesMapper: Ref<DatatypesMapperModel | null> = ref(null);
    const datatypesMapperStore = useDatatypesMapperStore();
    const datatypes: Ref<string[]> = ref([]);

    async function getDatatypesMapper() {
        try {
            await datatypesMapperStore.createMapper();
            datatypesMapper.value = datatypesMapperStore.datatypesMapper;
            if (datatypesMapperStore.datatypesMapper) {
                datatypes.value = datatypesMapperStore.datatypesMapper.datatypes;
            }
        } catch (e) {
            console.error("unable to create datatypes mapper\n", e);
        } finally {
            datatypesMapperLoading.value = false;
        }
        if (!datatypesMapperStore.datatypesMapper) {
            throw "Error creating datatypesMapper";
        }
    }

    getDatatypesMapper();

    return { datatypes, datatypesMapper, datatypesMapperLoading };
}
