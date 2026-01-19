import { onMounted, type Ref, watch } from "vue";

import type { UploadMode } from "@/components/Panels/Upload/types";
import { type StagedUploadItem, useUploadStagingStore } from "@/stores/uploadStagingStore";

interface UseUploadStagingReturn {
    clear: () => void;
}

/**
 * Composable to synchronize a local reactive items ref with the upload staging store.
 *
 * Responsibilities:
 * - Restore staged items on mount (when navigating back to an upload method)
 * - Persist changes reactively (deep watch)
 * - Provide a single clear() helper for post-upload cleanup
 */
export function useUploadStaging<T extends StagedUploadItem>(
    mode: UploadMode,
    items: Ref<T[]>,
): UseUploadStagingReturn {
    const stagingStore = useUploadStagingStore();

    // Restore staged items on mount
    onMounted(() => {
        const staged = stagingStore.getItems<T>(mode);
        if (staged.length > 0) {
            items.value = [...staged];
        }
    });

    // Persist changes
    watch(
        items,
        (value) => {
            stagingStore.setItems(mode, value);
        },
        { deep: true },
    );

    function clear() {
        stagingStore.clearItems(mode);
    }

    return {
        clear,
    };
}
