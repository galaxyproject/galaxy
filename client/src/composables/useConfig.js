import { computed, onMounted } from "vue";
import store from "store";

/* composable config wrapper */
export function useConfig() {
    const config = computed(() => store.getters["config/config"]);
    const isLoaded = computed(() => store.getters["config/configIsLoaded"]);

    // Anytime we mount this (for now), make sure to load.
    onMounted(() => {
        store.dispatch("config/loadConfigs");
    });

    return { config, isLoaded };
}
