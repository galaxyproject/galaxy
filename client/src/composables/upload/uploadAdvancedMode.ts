import type { Ref } from "vue";

import { useUserLocalStorage } from "@/composables/userLocalStorage";

/**
 * Shared state for upload panel advanced mode.
 * All components calling this composable will share the same reactive reference.
 */
let sharedAdvancedMode: Ref<boolean> | null = null;

/**
 * Composable for managing the upload panel's advanced mode setting.
 * This setting is persisted in user-specific localStorage and shared across all upload components.
 *
 * When advanced mode is disabled, the POSIX line ending option is hidden in upload tables.
 *
 * @returns An object containing the reactive advanced mode toggle state
 */
export function useUploadAdvancedMode() {
    if (!sharedAdvancedMode) {
        sharedAdvancedMode = useUserLocalStorage<boolean>("uploadPanel.advancedMode", false);
    }

    return {
        advancedMode: sharedAdvancedMode,
    };
}
