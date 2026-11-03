import type { Decorator } from "@storybook/vue3-vite";
import { h } from "vue";

import { useConfigStore } from "@/stores/configurationStore";

/**
 * Renders the story once the configuration has loaded, as the app does, for components whose
 * template reads the config on creation (the tool card's options menu).
 */
export const withLoadedConfig: Decorator = (story) => ({
    setup() {
        const configStore = useConfigStore();
        return () => (configStore.isLoaded ? h(story()) : null);
    },
});
