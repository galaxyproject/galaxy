import { storeToRefs } from "pinia";
import { computed } from "vue";

import { useObjectStoreStore } from "@/stores/objectStoreStore";

export function useSelectableObjectStores() {
    const store = useObjectStoreStore();
    const { selectableObjectStores } = storeToRefs(store);

    const hasSelectableObjectStores = computed(() => {
        return selectableObjectStores.value && selectableObjectStores.value.length > 0;
    });

    return {
        selectableObjectStores,
        hasSelectableObjectStores,
    };
}
