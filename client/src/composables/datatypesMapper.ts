import { type Ref, ref } from "vue";

import { type DatatypesMapperModel } from "@/components/Datatypes/model";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";

export function useDatatypesMapper() {
    const datatypesMapperLoading = ref(true);
    const datatypesMapper: Ref<DatatypesMapperModel | null> = ref(null);
    const datatypesMapperStore = useDatatypesMapperStore();
    const datatypes: Ref<string[]> = ref([]);

    async function getDatatypesMapper() {
        await datatypesMapperStore.createMapper();
        datatypesMapperLoading.value = datatypesMapperStore.loading;
        datatypesMapper.value = datatypesMapperStore.datatypesMapper;
        if (datatypesMapperStore.datatypesMapper) {
            datatypes.value = datatypesMapperStore.datatypesMapper.datatypes;
        }
    }

    getDatatypesMapper();

    return { datatypes, datatypesMapper, datatypesMapperLoading };
}
