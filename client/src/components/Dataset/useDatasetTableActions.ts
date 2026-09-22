import { faCopy, faEye, faFire, faTrash } from "@fortawesome/free-solid-svg-icons";
import { storeToRefs } from "pinia";

import type { HDASummary, HistoryItemSummary } from "@/api";
import { copyDataset, deleteDataset } from "@/api/datasets";
import type { TableAction } from "@/components/Common/GTable.types";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { Toast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";

export function useDatasetTableActions(refreshList: () => Promise<void>) {
    const historyStore = useHistoryStore();
    const { currentHistoryId } = storeToRefs(historyStore);

    const { confirm } = useConfirmDialog();

    async function onShowDataset(item: HistoryItemSummary) {
        const { history_id } = item;
        const filters = {
            deleted: item.deleted,
            visible: item.visible,
            hid: item.hid,
        };

        try {
            await historyStore.applyFilters(history_id, filters);
        } catch (error) {
            Toast.error("Failed to show dataset in history");
        }
    }

    async function onCopyDataset(item: HistoryItemSummary) {
        try {
            if (!currentHistoryId.value) {
                throw new Error("No current history found.");
            }

            await copyDataset(item.id, currentHistoryId.value, item.history_content_type);

            historyStore.loadCurrentHistory();
            await refreshList();
            const contentType = item.history_content_type === "dataset" ? "Dataset" : "Collection";
            Toast.success(`${contentType} "${item.name}" copied to current history.`);
        } catch (error) {
            Toast.error("Failed to copy history content");
        }
    }

    async function confirmDeleteDataset(item: HDASummary, purge: boolean) {
        const confirmed = await confirm(
            `Are you sure you want to ${purge ? "purge" : "delete"} the dataset "${item.name}"?`,
            {
                title: purge ? "Purge Dataset" : "Delete Dataset",
                okText: purge ? "Purge" : "Delete",
                okColor: "red",
                okIcon: purge ? faFire : faTrash,
            },
        );

        if (confirmed) {
            try {
                await deleteDataset(item.id, purge);

                Toast.success(`Dataset "${item.name}" ${purge ? "purged" : "deleted"}.`);
                historyStore.loadCurrentHistory();
                await refreshList();
            } catch (error) {
                Toast.error(`Failed to ${purge ? "purge" : "delete"} dataset.`);
            }
        }
    }

    async function onDeleteDataset(item: HDASummary) {
        confirmDeleteDataset(item, false);
    }

    async function onPurgeDataset(item: HDASummary) {
        confirmDeleteDataset(item, true);
    }

    const datasetTableActions: TableAction[] = [
        {
            id: "copy-dataset",
            label: "Copy to current history",
            title: "Copy Dataset to current history",
            icon: faCopy,
            handler: onCopyDataset,
        },
        {
            id: "show-dataset",
            label: "Show in history",
            title: "Show dataset in history panel",
            icon: faEye,
            handler: onShowDataset,
        },
        {
            id: "delete-dataset",
            label: "Delete",
            title: "Delete dataset",
            icon: faTrash,
            handler: onDeleteDataset,
        },
        {
            id: "purge-dataset",
            label: "Purge",
            title: "Purge dataset",
            icon: faFire,
            handler: onPurgeDataset,
        },
    ];

    return {
        datasetTableActions,
    };
}
