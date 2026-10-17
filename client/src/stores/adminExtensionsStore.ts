import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { type components, GalaxyApi } from "@/api";
import { errorMessageAsString } from "@/utils/simple-error";

export type AdminExtension = components["schemas"]["AdminExtension"];
export type AdminExtensionItem = AdminExtension["items"][number];

/** Loads the Admin panel extensions declared on the server. Only admins can read them. */
export const useAdminExtensionsStore = defineStore("adminExtensionsStore", () => {
    const extensions = ref<AdminExtension[]>([]);
    const loading = ref(false);
    const loaded = ref(false);
    const errorMessage = ref<string | null>(null);

    async function loadExtensions() {
        if (loaded.value || loading.value) {
            return;
        }
        loading.value = true;
        errorMessage.value = null;
        const { data, error } = await GalaxyApi().GET("/api/admin/extensions");
        if (error) {
            errorMessage.value = errorMessageAsString(error);
        } else {
            extensions.value = data;
            loaded.value = true;
        }
        loading.value = false;
    }

    const getItem = computed(() => {
        return (extensionId: string, itemId: string): AdminExtensionItem | undefined => {
            const extension = extensions.value.find((e) => e.id === extensionId);
            return extension?.items.find((i) => i.id === itemId);
        };
    });

    return {
        extensions,
        loading,
        loaded,
        errorMessage,
        loadExtensions,
        getItem,
    };
});
