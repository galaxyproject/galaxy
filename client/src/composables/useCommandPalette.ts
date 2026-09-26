import { computed, ref, unref } from "vue";

import { useConfig } from "@/composables/config";
import { useUserStore } from "@/stores/userStore";

/**
 * Shared open/close state for the global command palette. The palette
 * component is mounted once in `entry/analysis/App.vue`; any consumer
 * (hotkey, masthead button) can open it through this composable.
 */
const isPaletteOpen = ref(false);

export function useCommandPalette() {
    const { config, isConfigLoaded } = useConfig();
    const userStore = useUserStore();

    /**
     * Whether the instance offers the palette to the current user at all. The
     * configuration has to have landed first: until it does an instance that
     * turned the palette off would still answer ctrl/cmd+k.
     */
    const paletteEnabled = computed(() => {
        if (!unref(isConfigLoaded) || config.value?.enable_command_palette === false) {
            return false;
        }
        return !userStore.isAnonymous || config.value?.command_palette_allow_anonymous !== false;
    });

    function openPalette() {
        if (!paletteEnabled.value) {
            return;
        }
        isPaletteOpen.value = true;
    }

    function closePalette() {
        isPaletteOpen.value = false;
    }

    function togglePalette() {
        if (!paletteEnabled.value) {
            return;
        }
        isPaletteOpen.value = !isPaletteOpen.value;
    }

    return { isPaletteOpen, paletteEnabled, openPalette, closePalette, togglePalette };
}
