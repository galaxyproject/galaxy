import { defineStore } from "pinia";
import { ref } from "vue";

export interface ExportableItem {
    historyId: string;
    contentType: "dataset" | "dataset_collection";
    contentId: string;
    contentName: string;
}

/**
 * The item whose "Export to another Galaxy" dialog is open. The dialog is mounted once at the app root,
 * so it keeps its styling and survives the item being collapsed or scrolled out of the history panel.
 */
export const useExportToAnotherGalaxyStore = defineStore("exportToAnotherGalaxyStore", () => {
    const item = ref<ExportableItem | null>(null);

    function open(newItem: ExportableItem) {
        item.value = newItem;
    }

    function close() {
        item.value = null;
    }

    return { item, open, close };
});
