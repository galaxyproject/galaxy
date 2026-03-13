import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { onUnmounted, type Ref, ref } from "vue";

import type { ComponentColor, ComponentSize } from "@/components/BaseComponents/componentVariants";
import type ConfirmDialogComponent from "@/components/ConfirmDialog.vue";

/**
 * Bootstrap Vue modal message box options interface.
 * Based on https://bootstrap-vue.org/docs/components/modal#modal-message-boxes
 */
export interface ConfirmDialogOptions {
    /**
     * Modal title
     * @default "Please Confirm"
     */
    title?: string;
    /**
     * Modal size: 'small', 'medium, 'large'
     * @default undefined (medium)
     */
    size?: ComponentSize;
    /**
     * What color scheme to use for the OK button
     * @default undefined (grey)
     */
    okColor?: ComponentColor;
    /**
     * An optional FontAwesome icon to display in the OK button
     * @default undefined (no icon)
     */
    okIcon?: IconDefinition;
    /**
     * Text for OK button
     * @default "OK"
     */
    okText?: string;
    /**
     * Text for cancel button
     * @default "Cancel"
     */
    cancelText?: string;
    /**
     * Footer button size: 'small', 'medium, 'large'
     * @default undefined (medium)
     */
    buttonSize?: ComponentSize;
    /**
     * An AbortSignal that cancels the dialog when aborted.
     * Injected automatically by `useConfirmDialog` on caller unmount.
     */
    signal?: AbortSignal;
}

/**
 * Default configuration for confirm dialogs.
 * Can be modified to change application-wide defaults.
 */
export const DEFAULT_CONFIRM_OPTIONS: Partial<ConfirmDialogOptions> = {
    title: "Please Confirm",
    okText: "OK",
    cancelText: "Cancel",
    okColor: "blue",
} as const;

/**
 * Reference to the confirm dialog component instance
 */
const confirmDialogRef: Ref<InstanceType<typeof ConfirmDialogComponent> | null> = ref(null);

/**
 * Sets the confirm dialog component reference.
 * @param newRef - The new component reference
 */
export const setConfirmDialogComponentRef = (newRef: InstanceType<typeof ConfirmDialogComponent> | null): void => {
    confirmDialogRef.value = newRef;
};

/**
 * Internal function to validate and normalize confirm dialog options.
 * @param options - Raw options to normalize
 * @returns Normalized options with defaults applied
 */
function normalizeConfirmOptions(options: ConfirmDialogOptions | string): ConfirmDialogOptions {
    // Handle backward compatibility: if options is a string, treat it as title
    const baseOptions: ConfirmDialogOptions = typeof options === "string" ? { title: options } : options;

    return {
        ...DEFAULT_CONFIRM_OPTIONS,
        ...baseOptions,
    };
}

/**
 * Direct export for Options API components.
 * For Composition API, use `useConfirmDialog` instead.
 */
export const ConfirmDialog = {
    /**
     * Shows a confirmation dialog to the user.
     * @param message - The confirmation message to display
     * @param options - Dialog options object or title string (for backward compatibility)
     * @returns Promise resolving to `true` if confirmed, `false` if cancelled/closed
     * @throws {Error} When confirm dialog component reference is not set
     */
    async confirm(message: string, options: ConfirmDialogOptions | string = {}): Promise<boolean> {
        if (!confirmDialogRef.value) {
            throw new Error(
                "Confirm dialog component reference not set. " +
                    "Call setConfirmDialogComponentRef() during app initialization.",
            );
        }

        if (typeof message !== "string" || message.trim().length === 0) {
            throw new Error("Confirm dialog message must be a non-empty string.");
        }

        const normalizedOptions = normalizeConfirmOptions(options);

        try {
            return await confirmDialogRef.value.confirm(message, normalizedOptions);
        } catch (error) {
            console.error("Confirm dialog error:", error);
            // Gracefully handle component errors by returning false (cancelled)
            return false;
        }
    },
};

/**
 * Composable for using confirm dialog in Composition API components.
 * Returns a stable reference to avoid unnecessary re-renders.
 *
 * @returns Object containing confirm dialog methods
 */
export function useConfirmDialog() {
    const controller = new AbortController();
    onUnmounted(() => controller.abort());

    return {
        confirm: (message: string, options: ConfirmDialogOptions | string = {}) => {
            const normalizedOptions = typeof options === "string" ? { title: options } : options;
            return ConfirmDialog.confirm(message, { ...normalizedOptions, signal: controller.signal });
        },
    };
}
