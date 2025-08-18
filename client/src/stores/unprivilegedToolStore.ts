import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { GalaxyApi, type UnprivilegedToolResponse } from "@/api";

export const useUnprivilegedToolStore = defineStore("unprivilegedToolStore", () => {
    const unprivilegedTools = ref<UnprivilegedToolResponse[]>();
    const canUseUnprivilegedTools = ref(false);
    const isLoading = ref(false);
    const isLoaded = computed(() => unprivilegedTools.value !== undefined);

    async function load(reload = false) {
        if (reload || (!isLoaded.value && !isLoading.value)) {
            isLoading.value = true;
            const { data, error } = await GalaxyApi().GET("/api/unprivileged_tools");

            if (error) {
                canUseUnprivilegedTools.value = false;
            } else {
                unprivilegedTools.value = data;
                canUseUnprivilegedTools.value = true;

                isLoading.value = false;
            }
        }
        return unprivilegedTools;
    }

    load();
    return {
        canUseUnprivilegedTools,
        unprivilegedTools,
        isLoaded,
        load,
    };
});
