import { computed } from "vue";

import { useConfig } from "./config";

export function useStorageLocationConfiguration() {
    const { config } = useConfig();

    const isOnlyPreference = computed(() => {
        return !config.value || !config.value?.object_store_always_respect_user_selection;
    });

    return {
        isOnlyPreference,
    };
}
