import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { fetcher } from "@/api/schema";

// Temporary set to any until schema model is defined
export type GalaxyConfiguration = any;

const fetchConfiguration = fetcher.path("/api/configuration").method("get").create();

export const useConfigStore = defineStore("configurationStore", () => {
    const config = ref<GalaxyConfiguration>(null);
    const isLoading = ref(false);
    const isLoaded = computed(() => !!config.value);

    async function loadConfig() {
        if (!isLoaded.value && !isLoading.value) {
            isLoading.value = true;
            try {
                const { data } = await fetchConfiguration({});
                config.value = data;
                console.debug("Galaxy configuration loaded", config.value);
            } catch (err) {
                console.error("Error loading Galaxy configuration", err);
            } finally {
                isLoading.value = false;
            }
        }
    }

    function setConfiguration(configuration: GalaxyConfiguration) {
        config.value = configuration;
    }

    loadConfig();

    return {
        config,
        isLoaded,
        loadConfig,
        setConfiguration,
    };
});
