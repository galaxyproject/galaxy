import { computed, onMounted, inject } from "vue";

/* composable config wrapper */
export function useConfig(fetchOnce = false) {
    const store = inject("store");

    const config = computed(() => store.getters["config/config"]);
    const isLoaded = computed(() => store.getters["config/configIsLoaded"]);

    // Anytime we mount this (for now), make sure to load.
    onMounted(() => {
        if (!(fetchOnce && isLoaded)) {
            store.dispatch("config/loadConfigs");
        }
    });

    return { config, isLoaded };
}
