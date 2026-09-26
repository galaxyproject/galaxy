/**
 * Composable for managing upload default values and configurations.
 * Centralizes fetching of upload configurations and provides helpers for creating items with defaults.
 */

import { computed } from "vue";

import type { BaseUploadItem } from "@/components/Panels/Upload/types/uploadItem";
import { uploadOptionDefaults } from "@/composables/upload/uploadOptionModel";
import { useUploadConfigurations } from "@/composables/uploadConfigurations";

export function useUploadDefaults(formats?: string[]) {
    const { configOptions, effectiveExtensions, compositeExtensions, listDbKeys, ready } =
        useUploadConfigurations(formats);

    const defaultExtension = computed(() => configOptions.value?.defaultExtension || "auto");
    const defaultDbKey = computed(() => configOptions.value?.defaultDbKey || "?");

    /**
     * Creates an object with default values for common upload item properties
     */
    function createItemDefaults(): Omit<BaseUploadItem, "name"> {
        return {
            extension: defaultExtension.value,
            dbkey: defaultDbKey.value,
            spaceToTab: uploadOptionDefaults.spaceToTab,
            toPosixLines: uploadOptionDefaults.toPosixLines,
            autoDecompress: uploadOptionDefaults.autoDecompress,
        };
    }

    return {
        configOptions,
        effectiveExtensions,
        compositeExtensions,
        listDbKeys,
        configurationsReady: ready,
        defaultExtension,
        defaultDbKey,
        createItemDefaults,
    };
}
