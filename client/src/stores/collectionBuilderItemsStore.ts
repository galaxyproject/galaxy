import { defineStore } from "pinia";
import { ref } from "vue";

import type { HistoryItemSummary } from "@/api";
import type { ShowElementExtensionFunction } from "@/components/Collections/common/useExtensionFilter";

/**
 * Stores the history items selected for collection building.
 */
export const useCollectionBuilderItemSelection = defineStore("collectionBuilderItemSelection", () => {
    const selectedItems = ref<HistoryItemSummary[]>([]);

    function setSelectedItems(newSelectedItems: HistoryItemSummary[]) {
        selectedItems.value = newSelectedItems;
    }

    return { selectedItems, setSelectedItems };
});

export const usePairingDatasetTargetsStore = defineStore("pairingDatasetTargets", {
    state: () => ({
        // Currently dragged node (null if no drag in progress)
        draggedNodeId: null as string | null,
        // Current drop target node (null if no target)
        dropTargetId: null as string | null,
        // If a link has been clicked, it will marked here
        unpairedTarget: null as string | null,
        showElementExtension: null as ShowElementExtensionFunction | null,
    }),
    actions: {
        setShowElementExtension(func: ShowElementExtensionFunction) {
            this.showElementExtension = func;
        },
        getShowElementExtension() {
            return this.showElementExtension;
        },
        // Start dragging a node by its ID
        startDrag(nodeId: string) {
            this.draggedNodeId = nodeId;
        },
        // Set the current drop target by its ID
        setDropTarget(nodeId: string | null) {
            this.dropTargetId = nodeId;
        },
        // Clear drag state
        endDrag() {
            this.draggedNodeId = null;
            this.dropTargetId = null;
        },
        setUnpairedTarget(targetId: string) {
            this.unpairedTarget = targetId;
        },
        resetUnpairedTarget() {
            this.unpairedTarget = null;
        },
    },
});
