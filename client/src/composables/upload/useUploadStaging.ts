import { storeToRefs } from "pinia";
import { computed, onMounted, type Ref, watch } from "vue";

import type { UploadMethod } from "@/components/Panels/Upload/types";
import type { PasteContentItem } from "@/components/Panels/Upload/types/uploadItem";
import type { StagedUploadItem } from "@/stores/uploadStagingStore";
import { useUploadStagingStore } from "@/stores/uploadStagingStore";

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
    mode: UploadMethod,
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

export function useUploadStagingCounts() {
    const { itemsByMode } = storeToRefs(useUploadStagingStore());

    return computed<Partial<Record<UploadMethod, number>>>(() => {
        const counts: Partial<Record<UploadMethod, number>> = {};
        for (const [mode, items] of Object.entries(itemsByMode.value)) {
            const uploadMode = mode as UploadMethod;
            counts[uploadMode] = countStagedItems(uploadMode, items ?? []);
        }
        return counts;
    });
}

function countStagedItems(mode: UploadMethod, items: StagedUploadItem[]): number {
    if (mode == "paste-content") {
        return items.filter(isNonEmptyPasteContentItem).length;
    }
    return items.length;
}

function isNonEmptyPasteContentItem(item: StagedUploadItem): item is PasteContentItem {
    return isPasteContentItem(item) && item.content.trim().length > 0;
}

export function isPasteContentItem(item: StagedUploadItem): item is PasteContentItem {
    return "content" in item;
}
