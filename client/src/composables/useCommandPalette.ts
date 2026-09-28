import { ref } from "vue";

/**
 * Shared open/close state for the global command palette. The palette
 * component is mounted once in `entry/analysis/App.vue`; any consumer
 * (hotkey, masthead button) can open it through this composable.
 */
const isPaletteOpen = ref(false);

export function useCommandPalette() {
    function openPalette() {
        isPaletteOpen.value = true;
    }

    function closePalette() {
        isPaletteOpen.value = false;
    }

    function togglePalette() {
        isPaletteOpen.value = !isPaletteOpen.value;
    }

    return { isPaletteOpen, openPalette, closePalette, togglePalette };
}
