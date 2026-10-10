import { computed, onMounted } from "vue";

import { useConfigStore } from "@/stores/configurationStore";

/* composable config wrapper */
export function useConfig() {
    const store = useConfigStore();

    const config = computed(() => store.config);
    const isConfigLoaded = computed(() => store.isLoaded);

    // Anytime we mount this (for now), make sure to load.
    // loadConfig() is a no-op once loaded or while a load is in flight.
    onMounted(() => {
        store.loadConfig();
    });

    return { config, isConfigLoaded };
}
