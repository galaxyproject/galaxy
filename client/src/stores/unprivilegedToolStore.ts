import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { GalaxyApi, type UnprivilegedToolResponse } from "@/api";
import { useToast } from "@/composables/toast";
import { errorMessageAsString } from "@/utils/simple-error";

export const useUnprivilegedToolStore = defineStore("unprivilegedToolStore", () => {
    const unprivilegedTools = ref<UnprivilegedToolResponse[]>();
    const canUseUnprivilegedTools = ref(false);
    const isLoading = ref(false);
    const isLoaded = computed(() => unprivilegedTools.value !== undefined);
    const toast = useToast();

    function reportLoadFailure(error: unknown) {
        toast.error(errorMessageAsString(error), "Failed to check access to custom tools");
    }

    async function load(reload = false) {
        if (reload || (!isLoaded.value && !isLoading.value)) {
            isLoading.value = true;
            try {
                const { data, error, response } = await GalaxyApi().GET("/api/unprivileged_tools");

                if (error) {
                    canUseUnprivilegedTools.value = false;
                    // A 403 means the user lacks the role to run custom tools.
                    if (response.status !== 403) {
                        reportLoadFailure(error);
                    }
                } else {
                    unprivilegedTools.value = data;
                    canUseUnprivilegedTools.value = true;
                }
            } catch (e) {
                canUseUnprivilegedTools.value = false;
                reportLoadFailure(e);
            } finally {
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
