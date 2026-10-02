import { defineStore, storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { GalaxyApi, isRegisteredUser, type UnprivilegedToolResponse } from "@/api";
import { useToast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";
import { errorMessageAsString } from "@/utils/simple-error";

export const useUnprivilegedToolStore = defineStore("unprivilegedToolStore", () => {
    const unprivilegedTools = ref<UnprivilegedToolResponse[]>();
    const canUseUnprivilegedTools = ref(false);
    const isLoading = ref(false);
    const isLoaded = computed(() => unprivilegedTools.value !== undefined);
    const toast = useToast();
    const { currentUser } = storeToRefs(useUserStore());

    function reportLoadFailure(error: unknown) {
        toast.error(errorMessageAsString(error), "Failed to check access to custom tools");
    }

    async function load(reload = false) {
        // Anonymous users have no custom tools. The user watch below loads once a registered user is known.
        if (!isRegisteredUser(currentUser.value)) {
            return unprivilegedTools;
        }
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

    watch(
        () => (isRegisteredUser(currentUser.value) ? currentUser.value.id : null),
        (userId) => {
            if (userId) {
                load(true);
            } else {
                unprivilegedTools.value = undefined;
                canUseUnprivilegedTools.value = false;
            }
        },
        { immediate: true },
    );

    return {
        canUseUnprivilegedTools,
        unprivilegedTools,
        isLoaded,
        load,
        deactivateTool,
    };
});
