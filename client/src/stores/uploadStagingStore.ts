import { defineStore } from "pinia";
import { ref } from "vue";

import type { UploadMethod } from "@/components/Panels/Upload/types";
import type {
    LibraryDatasetItem,
    LocalFileItem,
    PasteContentItem,
    PasteUrlItem,
    RemoteFileItem,
} from "@/components/Panels/Upload/types/uploadItem";

/**
 * Union of all supported staged upload item types.
 * These match the component-level item types before mapping
 * to upload queue items.
 */
export type StagedUploadItem = LocalFileItem | PasteContentItem | PasteUrlItem | RemoteFileItem | LibraryDatasetItem;

export type StagedUploadItemsByMode = Partial<Record<UploadMethod, StagedUploadItem[]>>;

export const useUploadStagingStore = defineStore("uploadStagingStore", () => {
    const itemsByMode = ref<StagedUploadItemsByMode>({});

    function getItems<T extends StagedUploadItem = StagedUploadItem>(mode: UploadMethod): T[] {
        return (itemsByMode.value[mode] ?? []) as T[];
    }

    function setItems<T extends StagedUploadItem>(mode: UploadMethod, items: T[]) {
        // always store a new array reference so reactivity triggers
        itemsByMode.value[mode] = [...items];
    }

    function clearItems(mode: UploadMethod) {
        delete itemsByMode.value[mode];
    }

    return {
        itemsByMode,
        getItems,
        setItems,
        clearItems,
    };
});
