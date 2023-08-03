import { computed, onMounted } from "vue";

import { useConfigStore } from "@/stores/configurationStore";

/* composable config wrapper */
export function useConfig(fetchOnce = false) {
    const store = useConfigStore();

    const config = computed(() => store.config);
    const isLoaded = computed(() => store.isLoaded);

    // Anytime we mount this (for now), make sure to load.
    onMounted(() => {
        if (!(fetchOnce && isLoaded)) {
            store.loadConfig();
        }
    });

    return { config, isLoaded };
}
