import { computed, type Ref } from "vue";

import { type Instance } from "@/api/configTemplates";

export function useFiltering<T extends Instance>(allInstances: Ref<T[]>) {
    const activeInstances = computed(() => {
        return allInstances.value.filter((item: T) => !item.hidden);
    });

    return {
        activeInstances,
    };
}
