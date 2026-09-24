import { computed, type ComputedRef, type Ref, ref } from "vue";

import { findExtension } from "@/components/Upload/utils";
import type { ExtensionDetails } from "@/composables/uploadConfigurations";

/**
 * Base interface for upload items that support bulk operations.
 * Upload items must have these properties to work with bulk operations.
 * The deferred property is optional since not all upload types support it (e.g., local files).
 */
export interface BulkUploadItem {
    extension: string;
    dbkey: string;
    spaceToTab: boolean;
    toPosixLines: boolean;
    autoDecompress: boolean;
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
    allAutoDecompress: ComputedRef<boolean>;
    allDeferred: ComputedRef<boolean>;

    // Indeterminate states for checkboxes
    spaceToTabIndeterminate: ComputedRef<boolean>;
    toPosixLinesIndeterminate: ComputedRef<boolean>;
    autoDecompressIndeterminate: ComputedRef<boolean>;
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
    toggleAllAutoDecompress: () => void;
    toggleAllDeferred: () => void;
}

interface BooleanBulkOptionConfig<T extends BulkUploadItem> {
    isEnabled: (item: T) => boolean;
    setValue: (item: T, value: boolean) => void;
}

function createBooleanBulkOptionState<T extends BulkUploadItem>(items: Ref<T[]>, config: BooleanBulkOptionConfig<T>) {
    const allEnabled = computed(() => {
        return items.value.length > 0 && items.value.every((item) => config.isEnabled(item));
    });

    const indeterminate = computed(() => {
        return items.value.length > 0 && items.value.some((item) => config.isEnabled(item)) && !allEnabled.value;
    });

    function toggleAll() {
        const newValue = !allEnabled.value;
        items.value.forEach((item) => {
            config.setValue(item, newValue);
        });
    }

    return {
        allEnabled,
        indeterminate,
        toggleAll,
    };
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

    const spaceToTabState = createBooleanBulkOptionState(items, {
        isEnabled: (item) => item.spaceToTab === true,
        setValue: (item, value) => {
            item.spaceToTab = value;
        },
    });

    const toPosixLinesState = createBooleanBulkOptionState(items, {
        isEnabled: (item) => item.toPosixLines === true,
        setValue: (item, value) => {
            item.toPosixLines = value;
        },
    });

    const autoDecompressState = createBooleanBulkOptionState(items, {
        isEnabled: (item) => item.autoDecompress === true,
        setValue: (item, value) => {
            item.autoDecompress = value;
        },
    });

    const deferredState = createBooleanBulkOptionState(items, {
        isEnabled: (item) => item.deferred === true,
        setValue: (item, value) => {
            if (item.deferred !== undefined) {
                item.deferred = value;
            }
        },
    });

    const allSpaceToTab = spaceToTabState.allEnabled;
    const allToPosixLines = toPosixLinesState.allEnabled;
    const allAutoDecompress = autoDecompressState.allEnabled;
    const allDeferred = deferredState.allEnabled;

    const spaceToTabIndeterminate = spaceToTabState.indeterminate;
    const toPosixLinesIndeterminate = toPosixLinesState.indeterminate;
    const autoDecompressIndeterminate = autoDecompressState.indeterminate;
    const deferredIndeterminate = deferredState.indeterminate;

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
            item.extension = extension;
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
            item.dbkey = dbKey;
        });
    }

    const toggleAllSpaceToTab = spaceToTabState.toggleAll;
    const toggleAllToPosixLines = toPosixLinesState.toggleAll;
    const toggleAllAutoDecompress = autoDecompressState.toggleAll;
    const toggleAllDeferred = deferredState.toggleAll;

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
        allAutoDecompress,
        allDeferred,
        spaceToTabIndeterminate,
        toPosixLinesIndeterminate,
        autoDecompressIndeterminate,
        deferredIndeterminate,
        getExtensionWarning,
        bulkExtensionWarning,
        setAllExtensions,
        setAllDbKeys,
        toggleAllSpaceToTab,
        toggleAllToPosixLines,
        toggleAllAutoDecompress,
        toggleAllDeferred,
    };
}
