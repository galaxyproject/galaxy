import { computed, ref, unref } from "vue";

import { useConfig } from "@/composables/config";

/**
 * Shared open/close state for the global command palette. The palette
 * component is mounted once in `entry/analysis/App.vue`; any consumer
 * (hotkey, masthead button) can open it through this composable.
 */
const isPaletteOpen = ref(false);

export function useCommandPalette() {
    const { config, isConfigLoaded } = useConfig();

    /**
     * Whether the instance offers the palette at all, to anonymous and registered users alike. The
     * configuration has to have landed first: until it does an instance that
     * turned the palette off would still answer ctrl/cmd+k.
     */
    const paletteEnabled = computed(() => unref(isConfigLoaded) && config.value?.enable_command_palette !== false);

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
