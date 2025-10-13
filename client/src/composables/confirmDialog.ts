import { type Ref, ref } from "vue";

/**
 * Bootstrap Vue variants for styling components.
 */
export type BootstrapVariant =
    | "primary"
    | "secondary"
    | "success"
    | "warning"
    | "danger"
    | "info"
    | "light"
    | "dark"
    | "outline-primary"
    | "outline-secondary"
    | "outline-success"
    | "outline-warning"
    | "outline-danger"
    | "outline-info"
    | "outline-light"
    | "outline-dark";

/**
 * Bootstrap Vue modal message box options interface.
 * Based on https://bootstrap-vue.org/docs/components/modal#modal-message-boxes
 */
export interface ConfirmDialogOptions {
    /**
     * Unique identifier for the modal
     */
    id?: string;
    /**
     * Modal title
     * @default "Please Confirm"
     */
    title?: string;
    /**
     * CSS classes for title
     * @default "h-md"
     */
    titleClass?: string;
    /**
     * Modal size: 'sm', 'lg', 'xl'
     * @default undefined (medium)
     */
    size?: "sm" | "lg" | "xl";
    /**
     * Center modal vertically
     * @default true
     */
    centered?: boolean;
    /**
     * Make modal body scrollable
     * @default false
     */
    scrollable?: boolean;
    /**
     * Text for OK button
     * @default "OK"
     */
    okTitle?: string;
    /**
     * Bootstrap variant for OK button
     * @default "primary"
     */
    okVariant?: BootstrapVariant;
    /**
     * Text for cancel button
     * @default "Cancel"
     */
    cancelTitle?: string;
    /**
     * Bootstrap variant for cancel button
     * @default "outline-primary"
     */
    cancelVariant?: BootstrapVariant;
    /**
     * Footer button size: 'sm', 'lg'
     * @default undefined (normal)
     */
    buttonSize?: "sm" | "lg";
    /**
     * Hide header close button
     * @default false
     */
    hideHeaderClose?: boolean;
    /**
     * CSS classes for header
     */
    headerClass?: string;
    /**
     * Background variant for header
     */
    headerBgVariant?: BootstrapVariant;
    /**
     * Text variant for header
     */
    headerTextVariant?: BootstrapVariant;
    /**
     * CSS classes for modal body
     */
    bodyClass?: string;
    /**
     * Background variant for body
     */
    bodyBgVariant?: BootstrapVariant;
    /**
     * Text variant for body
     */
    bodyTextVariant?: BootstrapVariant;
    /**
     * CSS classes for footer
     */
    footerClass?: string;
    /**
     * Background variant for footer
     */
    footerBgVariant?: BootstrapVariant;
    /**
     * Text variant for footer
     */
    footerTextVariant?: BootstrapVariant;
    /**
     * Prevent closing on backdrop click
     * @default false
     */
    noCloseOnBackdrop?: boolean;
    /**
     * Prevent closing on ESC key
     * @default false
     */
    noCloseOnEsc?: boolean;
    /**
     * Auto-focus button: 'ok', 'cancel', 'close'
     * @default undefined
     */
    autoFocusButton?: "ok" | "cancel" | "close";
    /**
     * Element to return focus to
     * @default undefined
     */
    returnFocus?: string | HTMLElement;
    /**
     * CSS classes for modal container
     * @default undefined
     */
    modalClass?: string;
    /**
     * CSS classes for modal content
     * @default undefined
     */
    contentClass?: string;
    /**
     * Disable fade animation
     * @default false
     */
    noFade?: boolean;
    /**
     * Hide modal backdrop
     * @default false
     */
    hideBackdrop?: boolean;
}

/**
 * Interface for the confirm dialog component reference.
 */
interface ConfirmDialogComponent {
    confirm(message: string, options?: ConfirmDialogOptions): Promise<boolean>;
}

/**
 * Default configuration for confirm dialogs.
 * Can be modified to change application-wide defaults.
 */
export const DEFAULT_CONFIRM_OPTIONS: Partial<ConfirmDialogOptions> = {
    title: "Please Confirm",
    titleClass: "h-md",
    centered: true,
    okTitle: "OK",
    cancelTitle: "Cancel",
    okVariant: "primary",
    cancelVariant: "outline-primary",
    buttonSize: undefined, // Uses Bootstrap default size
    hideHeaderClose: false,
    noCloseOnBackdrop: false,
    noCloseOnEsc: false,
    noFade: false,
    hideBackdrop: false,
    scrollable: false,
} as const;

/**
 * Reference to the confirm dialog component instance
 */
let confirmDialogRef: Ref<ConfirmDialogComponent | null> = ref(null);

/**
 * Sets the confirm dialog component reference.
 * @param newRef - The new component reference
 */
export const setConfirmDialogComponentRef = (newRef: ConfirmDialogComponent | null): void => {
    // eslint-disable-next-line vue/no-ref-as-operand
    confirmDialogRef = ref(newRef);
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
    return { ...ConfirmDialog };
}
