import { defineStore } from "pinia";
import { ref } from "vue";

import { fetcher } from "@/schema";

// Temporary set to any until schema model is defined
type GalaxyConfiguration = any;

const fetchConfiguration = fetcher.path("/api/configuration").method("get").create();

export const useConfigStore = defineStore("configurationStore", () => {
    const config = ref<GalaxyConfiguration>(null);
    const isLoaded = ref(false);

    async function loadConfig() {
        if (!config.value) {
            try {
                const { data } = await fetchConfiguration({});
                config.value = data;
                isLoaded.value = true;
            } catch (err) {
                console.warn("Error loading Galaxy configuration", err);
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
