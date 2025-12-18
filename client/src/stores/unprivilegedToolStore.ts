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

    async function deactivateTool(uuid: string) {
        if (unprivilegedTools.value) {
            isLoading.value = true;
            const { error } = await GalaxyApi().DELETE("/api/unprivileged_tools/{uuid}", {
                params: { path: { uuid } },
            });

            if (!error) {
                unprivilegedTools.value = unprivilegedTools.value.filter((tool) => tool.uuid !== uuid);
            }
            isLoading.value = false;
        }
    }

    load();

    return {
        canUseUnprivilegedTools,
        unprivilegedTools,
        isLoaded,
        load,
        deactivateTool,
    };
});
