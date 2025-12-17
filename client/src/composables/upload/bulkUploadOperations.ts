import { computed, type ComputedRef, type Ref, ref } from "vue";

import { findExtension } from "@/components/Upload/utils";
import type { ExtensionDetails } from "@/composables/uploadConfigurations";

/**
 * Base interface for upload items that support bulk operations.
 * Upload items must have these properties to work with bulk operations.
 */
export interface BulkUploadItem {
    extension?: string;
    dbkey?: string;
    spaceToTab?: boolean;
    toPosixLines?: boolean;
    deferred?: boolean;
}

/**
 * Return type for the useBulkUploadOperations composable
 */
export interface BulkUploadOperations {
    // Bulk selectors
    bulkExtension: Ref<string>;
    bulkDbKey: Ref<string>;

    // "All" computed states
    allSpaceToTab: ComputedRef<boolean>;
    allToPosixLines: ComputedRef<boolean>;
    allDeferred: ComputedRef<boolean>;

    // Indeterminate states for checkboxes
    spaceToTabIndeterminate: ComputedRef<boolean>;
    toPosixLinesIndeterminate: ComputedRef<boolean>;
    deferredIndeterminate: ComputedRef<boolean>;

    // Extension warning functions
    getExtensionWarning: (extensionId: string) => string | undefined;
    bulkExtensionWarning: ComputedRef<string | undefined>;

    // Bulk setter functions
    setAllExtensions: (extension: string) => void;
    setAllDbKeys: (dbKey: string) => void;

    // Toggle functions for checkboxes
    toggleAllSpaceToTab: () => void;
    toggleAllToPosixLines: () => void;
    toggleAllDeferred: () => void;
}

/**
 * Composable for managing bulk operations on upload items.
 * Provides functionality for bulk setting extensions, database keys, toggling
 * upload settings (spaceToTab, toPosixLines, deferred), and extension warnings.
 *
 * @example
 * ```typescript
 * const items = ref<FileItem[]>([...]);
 * const { effectiveExtensions } = useUploadConfigurations();
 * const bulk = useBulkUploadOperations(items, effectiveExtensions);
 *
 * // Use in template
 * <BFormSelect v-model="bulk.bulkExtension.value" @change="bulk.setAllExtensions">
 * <BFormCheckbox :checked="bulk.allSpaceToTab.value" @change="bulk.toggleAllSpaceToTab">
 * <span v-if="bulk.bulkExtensionWarning">{{ bulk.bulkExtensionWarning }}</span>
 * ```
 *
 * @param items - Reactive reference to array of upload items
 * @param effectiveExtensions - Reactive reference to available extensions for warnings
 * @returns Object containing bulk operation state and functions
 */
export function useBulkUploadOperations<T extends BulkUploadItem>(
    items: Ref<T[]>,
    effectiveExtensions: Ref<ExtensionDetails[]>,
): BulkUploadOperations {
    // Bulk selectors for header dropdowns
    const bulkExtension = ref<string>("");
    const bulkDbKey = ref<string>("");

    /**
     * Computed property that returns true if all items have spaceToTab enabled.
     */
    const allSpaceToTab = computed(() => {
        return items.value.length > 0 && items.value.every((item) => item.spaceToTab === true);
    });

    /**
     * Computed property that returns true if all items have toPosixLines enabled.
     */
    const allToPosixLines = computed(() => {
        return items.value.length > 0 && items.value.every((item) => item.toPosixLines === true);
    });

    /**
     * Computed property that returns true if all items have deferred enabled.
     * Only relevant when supportDeferred option is true.
     */
    const allDeferred = computed(() => {
        return items.value.length > 0 && items.value.every((item) => item.deferred === true);
    });

    /**
     * Computed property for checkbox indeterminate state (some but not all checked).
     */
    const spaceToTabIndeterminate = computed(() => {
        return (
            items.value.length > 0 &&
            items.value.some((item) => item.spaceToTab === true) &&
            !items.value.every((item) => item.spaceToTab === true)
        );
    });

    /**
     * Computed property for checkbox indeterminate state (some but not all checked).
     */
    const toPosixLinesIndeterminate = computed(() => {
        return (
            items.value.length > 0 &&
            items.value.some((item) => item.toPosixLines === true) &&
            !items.value.every((item) => item.toPosixLines === true)
        );
    });

    /**
     * Computed property for checkbox indeterminate state (some but not all checked).
     */
    const deferredIndeterminate = computed(() => {
        return (
            items.value.length > 0 &&
            items.value.some((item) => item.deferred === true) &&
            !items.value.every((item) => item.deferred === true)
        );
    });

    /**
     * Sets the extension/type for all items in the list.
     * @param extension - The extension ID to set, or empty string to skip
     */
    function setAllExtensions(extension: string) {
        bulkExtension.value = extension;

        if (!extension || extension === "") {
            return;
        }

        items.value.forEach((item) => {
            if ("extension" in item) {
                item.extension = extension;
            }
        });
    }

    /**
     * Sets the database key for all items in the list.
     * @param dbKey - The database key to set, or empty string to skip
     */
    function setAllDbKeys(dbKey: string) {
        bulkDbKey.value = dbKey;

        if (!dbKey || dbKey === "") {
            return;
        }

        items.value.forEach((item) => {
            if ("dbkey" in item) {
                item.dbkey = dbKey;
            }
        });
    }

    /**
     * Toggles the spaceToTab setting for all items.
     * If all are currently enabled, disables all; otherwise enables all.
     */
    function toggleAllSpaceToTab() {
        const newValue = !allSpaceToTab.value;
        items.value.forEach((item) => {
            if ("spaceToTab" in item) {
                item.spaceToTab = newValue;
            }
        });
    }

    /**
     * Toggles the toPosixLines setting for all items.
     * If all are currently enabled, disables all; otherwise enables all.
     */
    function toggleAllToPosixLines() {
        const newValue = !allToPosixLines.value;
        items.value.forEach((item) => {
            if ("toPosixLines" in item) {
                item.toPosixLines = newValue;
            }
        });
    }

    /**
     * Toggles the deferred setting for all items.
     * If all are currently enabled, disables all; otherwise enables all.
     * Only relevant when supportDeferred option is true.
     */
    function toggleAllDeferred() {
        const newValue = !allDeferred.value;
        items.value.forEach((item) => {
            if ("deferred" in item) {
                item.deferred = newValue;
            }
        });
    }

    /**
     * Gets the upload warning for a specific extension ID.
     *
     * @param extensionId - The extension ID to look up
     * @returns The warning message or undefined if no warning exists
     */
    function getExtensionWarning(extensionId: string): string | undefined {
        const ext = findExtension(effectiveExtensions.value, extensionId);
        return ext?.upload_warning || undefined;
    }

    /**
     * Computed property for the bulk extension warning.
     * Updates when bulkExtension changes.
     */
    const bulkExtensionWarning = computed(() => {
        if (!bulkExtension.value || bulkExtension.value === "") {
            return undefined;
        }
        return getExtensionWarning(bulkExtension.value);
    });

    return {
        bulkExtension,
        bulkDbKey,
        allSpaceToTab,
        allToPosixLines,
        allDeferred,
        spaceToTabIndeterminate,
        toPosixLinesIndeterminate,
        deferredIndeterminate,
        getExtensionWarning,
        bulkExtensionWarning,
        setAllExtensions,
        setAllDbKeys,
        toggleAllSpaceToTab,
        toggleAllToPosixLines,
        toggleAllDeferred,
    };
}
