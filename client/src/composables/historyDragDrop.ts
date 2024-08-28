import { computed, type Ref, ref, unref } from "vue";

import { type DCEDataset, type DCESummary, type HistoryItemSummary, isDatasetElement, isHistoryItem } from "@/api";
import { copyDataset, type HistoryContentSource, type HistoryContentType } from "@/api/datasets";
import { Toast } from "@/composables/toast";
import { useEventStore } from "@/stores/eventStore";
import { useHistoryStore } from "@/stores/historyStore";

type DraggableHistoryItem = HistoryItemSummary | DCEDataset; // TODO: DCESummary instead of DCEDataset
interface HistoryItemCopyData {
    dataSource: HistoryContentSource;
    type: HistoryContentType;
    id: string;
}

export function useHistoryDragDrop(targetHistoryId?: Ref<string> | string, createNew = false, pinHistories = false) {
    // convert destinationHistoryId to a ref if it's not already
    const destinationHistoryId = computed(() => {
        if (typeof targetHistoryId === "string") {
            return targetHistoryId;
        }
        return unref(targetHistoryId);
    });

    const eventStore = useEventStore();
    const historyStore = useHistoryStore();

    const fromHistoryId = computed(() => {
        const dragItems = getDragItems();
        return dragItems[0]
            ? isHistoryItem(dragItems[0])
                ? dragItems[0].history_id
                : dragItems[0].object?.history_id
            : null;
    });

    const showDropZone = ref(false);
    const dragTarget = ref<EventTarget | null>(null);
    const processingDrop = ref(false);

    const operationDisabled = computed(
        () =>
            !fromHistoryId.value ||
            (destinationHistoryId.value && fromHistoryId.value === destinationHistoryId.value) ||
            (!createNew && !destinationHistoryId.value) ||
            !getDragItems().length ||
            processingDrop.value
    );

    function getDragItems() {
        const storeItems = eventStore.getDragItems();
        // Filter out any non-history or `DatasetCollectionElement` items
        return storeItems?.filter(
            (item) => isHistoryItem(item) || isDatasetElement(item as DCESummary)
        ) as DraggableHistoryItem[];
    }

    function onDragEnter(e: DragEvent) {
        if (operationDisabled.value) {
            return;
        }
        dragTarget.value = e.target;
        showDropZone.value = true;
    }

    function onDragOver(e: DragEvent) {
        if (operationDisabled.value) {
            return;
        }
        e.preventDefault();
    }

    function onDragLeave(e: DragEvent) {
        if (operationDisabled.value) {
            return;
        }
        if (dragTarget.value === e.target) {
            showDropZone.value = false;
        }
    }

    async function onDrop() {
        showDropZone.value = false;
        if (operationDisabled.value) {
            return;
        }
        processingDrop.value = true;

        let datasetCount = 0;
        let collectionCount = 0;

        try {
            const dragItems = getDragItems();
            const multiple = dragItems.length > 1;
            const originalHistoryId = fromHistoryId.value as string;

            let historyId;
            if (destinationHistoryId.value) {
                historyId = destinationHistoryId.value;
            } else if (createNew) {
                await historyStore.createNewHistory();
                historyId = historyStore.currentHistoryId;
            } else {
                historyId = null;
            }
            if (!historyId) {
                throw new Error("Destination history not found or created");
            }

            const copyableItems: HistoryItemCopyData[] = [];
            // iterate over the data array and get valid copyable items
            for (const item of dragItems) {
                let copyableItem: HistoryItemCopyData;
                if (isHistoryItem(item)) {
                    copyableItem = {
                        dataSource: item.history_content_type === "dataset" ? "hda" : "hdca",
                        type: item.history_content_type,
                        id: item.id,
                    };
                }
                // For DCEs, only `DCEDataset`s are droppable, `DCEDatasetCollection`s are not
                else if (isDatasetElement(item) && item.object) {
                    copyableItem = {
                        dataSource: "hda",
                        type: "dataset",
                        id: item.object.id,
                    };
                } else {
                    throw new Error(`Invalid item type${item.element_type ? `: ${item.element_type}` : ""}`);
                }
                copyableItems.push(copyableItem);
            }

            // iterate over the data array and copy each item to the current history
            for (const item of copyableItems) {
                const { dataSource, type, id } = item;
                await copyDataset(id, historyId, type, dataSource);

                if (dataSource === "hda") {
                    datasetCount++;
                    if (!multiple) {
                        Toast.info(`Dataset copied to ${createNew ? "new" : ""} history`);
                    }
                } else {
                    collectionCount++;
                    if (!multiple) {
                        Toast.info(`Collection copied to ${createNew ? "new" : ""} history`);
                    }
                }
            }

            if (multiple && datasetCount > 0) {
                Toast.info(
                    `${datasetCount} dataset${datasetCount > 1 ? "s" : ""} copied to ${createNew ? "new" : ""} history`
                );
            }
            if (multiple && collectionCount > 0) {
                Toast.info(
                    `${collectionCount} collection${collectionCount > 1 ? "s" : ""} copied to ${
                        createNew ? "new" : ""
                    } history`
                );
            }

            // if items were copied
            if (datasetCount > 0 && collectionCount > 0) {
                if (pinHistories && historyStore.pinnedHistories.length > 0) {
                    // pin the target history
                    historyStore.pinHistory(historyId);
                    // also pin the original history where the item came from
                    historyStore.pinHistory(originalHistoryId);
                } else {
                    historyStore.loadHistoryById(historyId);
                }
            }
        } catch (error) {
            Toast.error(`${error}`);
        } finally {
            processingDrop.value = false;
        }
    }

    return {
        showDropZone,
        onDragEnter,
        onDragOver,
        onDragLeave,
        onDrop,
    };
}
