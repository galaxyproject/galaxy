import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { GalaxyApi } from "@/api";
import { errorMessageAsString } from "@/utils/simple-error";

// Temporary set to any until schema model is defined
export type GalaxyConfiguration = any;

export const useConfigStore = defineStore("configurationStore", () => {
    const config = ref<GalaxyConfiguration>(null);
    const isLoading = ref(false);
    const loadError = ref("");
    const isLoaded = computed(() => !!config.value);

    async function loadConfig() {
        if (!isLoaded.value && !isLoading.value) {
            isLoading.value = true;
            try {
                const { data, error } = await GalaxyApi().GET("/api/configuration");

                if (error) {
                    throw new Error(errorMessageAsString(error));
                }

                config.value = data;
                loadError.value = "";
                if (process.env.NODE_ENV != "test") {
                    // an important debug message at runtime but not needed in testing
                    console.debug("Galaxy configuration loaded", config.value);
                }
            } catch (error) {
                loadError.value = errorMessageAsString(error);
            } finally {
                isLoading.value = false;
            }
        }
    }

    function setConfiguration(configuration: GalaxyConfiguration) {
        config.value = configuration;
        loadError.value = "";
    }

    loadConfig();

    return {
        config,
        isLoaded,
        loadError,
        loadConfig,
        setConfiguration,
    };
});
