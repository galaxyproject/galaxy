import {
    faBurn,
    faCopy,
    faExchangeAlt,
    faEye,
    faShareAlt,
    faTrash,
    faTrashRestore,
    faUndo,
    faUsers,
} from "@fortawesome/free-solid-svg-icons";
import { computed, type Ref } from "vue";

import { GalaxyApi } from "@/api";
import type { AnyHistoryEntry } from "@/api/histories";
import { isArchivedHistory, isMyHistory } from "@/api/histories";
import type { ArchivedHistorySummary } from "@/api/histories.archived";
import type { CardAction } from "@/components/Common/GCard.types";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { Toast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

export function useHistoryCardActions(
    history: Ref<AnyHistoryEntry>,
    archivedView: boolean,
    refreshCallBack: () => void
) {
    const { confirm } = useConfirmDialog();

    const historyStore = useHistoryStore();

    async function onDeleteHistory(purge = false) {
        const confirmed = await confirm(
            `Are you sure you want to ${purge ? "permanently delete" : "delete"} this history?`,
            {
                id: "delete-history",
                title: purge ? "Permanently Delete History" : "Delete History",
                okTitle: purge ? "Permanently Delete" : "Delete",
                okVariant: "danger",
                cancelVariant: "outline-primary",
                centered: true,
            }
        );

        if (confirmed) {
            try {
                await historyStore.deleteHistory(String(history.value.id), purge);
                refreshCallBack();
                Toast.success("History deleted");
            } catch (e) {
                Toast.error(`Failed to delete history: ${errorMessageAsString(e)}`);
            }
        }
    }

    async function onRestore() {
        try {
            await historyStore.restoreHistory(history.value.id);
            refreshCallBack();
            Toast.success("History restored");
        } catch (e) {
            Toast.error(`Failed to restore history: ${errorMessageAsString(e)}`);
        }
    }

    async function onImportCopy(hti: ArchivedHistorySummary) {
        const confirmed = await confirm(
            localize(
                `Are you sure you want to import a new copy of this history? This will create a new history with the same datasets contained in the associated export snapshot.`
            ),
            {
                id: "history-import-copy",
                title: localize(`Import Copy of '${hti.name}'?`),
            }
        );

        if (!confirmed) {
            return;
        }

        if (!hti.export_record_data) {
            Toast.error(
                localize(`Failed to import history '${hti.name}' because it does not have an export record.`),
                localize("History Import Failed")
            );
            return;
        }

        const { error } = await GalaxyApi().POST("/api/histories/from_store_async", {
            body: {
                model_store_format: hti.export_record_data?.model_store_format,
                store_content_uri: hti.export_record_data?.target_uri,
            },
        });

        if (error) {
            Toast.error(
                localize(`Failed to import history '${hti.name}' with reason: ${error}`),
                localize("History Import Failed")
            );
            return;
        }

        Toast.success(
            localize(
                `The History '${hti.name}' it's being imported. This process may take a while. Check your histories list after a few minutes.`
            ),
            localize("Importing History in background...")
        );
    }

    async function onRestoreHistory(htr: ArchivedHistorySummary) {
        const confirmMessage =
            htr.purged && htr.export_record_data
                ? localize(
                      "Are you sure you want to restore this (purged) history? Please note that this will not restore the datasets associated with this history. If you want to fully recover it, you can import a copy from the export record instead."
                  )
                : localize(
                      "Are you sure you want to restore this history? This will move the history back to your active histories."
                  );

        const confirmed = await confirm(confirmMessage, {
            id: "history-unarchive",
            title: localize(`Unarchive '${htr.name}'?`),
            okTitle: localize("Unarchive"),
            cancelVariant: "outline-primary",
            centered: true,
        });

        if (!confirmed) {
            return;
        }

        try {
            await historyStore.unarchiveHistoryById(htr.id, true);
            refreshCallBack();
            Toast.success(localize(`History '${htr.name}' has been restored.`), localize("History Restored"));
        } catch (error) {
            Toast.error(
                localize(`Failed to restore history '${htr.name}' with reason: ${error}`),
                localize("History Restore Failed")
            );
        }
    }

    const historyCardExtraActions: CardAction[] = [
        {
            id: "delete",
            label: localize("Delete"),
            title: localize("Delete this history"),
            icon: faTrash,
            handler: onDeleteHistory,
            visible: !history.value.deleted && isMyHistory(history.value),
        },
        {
            id: "purge",
            label: localize("Delete Permanently"),
            title: localize("Purge this history (permanently delete)"),
            icon: faBurn,
            handler: async () => await onDeleteHistory(true),
            visible: !history.value.purged && isMyHistory(history.value),
        },
    ];

    const historyCardSecondaryActions: CardAction[] = [
        {
            id: "change-permissions",
            label: localize("Change Permissions"),
            title: localize("Change permissions for this history"),
            icon: faUsers,
            to: `/histories/permissions?id=${history.value.id}`,
            visible: !history.value.deleted && isMyHistory(history.value),
        },
        {
            id: "share",
            label: localize("Share"),
            title: localize("Share this history"),
            icon: faShareAlt,
            variant: "outline-primary",
            to: `/histories/sharing?id=${history.value.id}`,
            visible: !history.value.deleted && isMyHistory(history.value),
        },
    ];

    const historyCardPrimaryActions = computed<CardAction[]>(() => {
        return [
            {
                id: "restore",
                title: localize("Restore this history"),
                label: localize("Restore"),
                variant: "outline-primary",
                icon: faTrashRestore,
                handler: onRestore,
                visible: history.value.deleted && !history.value.purged && isMyHistory(history.value),
            },
            {
                id: "switch",
                title: localize("Set as current history"),
                label: localize("Set as Current"),
                variant: "outline-primary",
                icon: faExchangeAlt,
                handler: () => historyStore.setCurrentHistory(String(history.value.id)),
                visible:
                    (isMyHistory(history.value) || archivedView) && historyStore.currentHistoryId !== history.value.id,
            },
            {
                title: "current history",
                id: "current",
                label: "Current",
                variant: "outline-primary",
                disabled: true,
                visible:
                    (isMyHistory(history.value) || archivedView) && historyStore.currentHistoryId === history.value.id,
            },
            {
                id: "import-copy",
                label: localize("Import Copy"),
                title: localize("Import a new copy of this history from the associated export record"),
                icon: faCopy,
                disabled:
                    isArchivedHistory(history.value) && history.value.export_record_data?.target_uri === undefined,
                variant: history.value.purged ? "primary" : "outline-primary",
                handler: () => onImportCopy(history.value),
                visible: isArchivedHistory(history.value) && history.value.export_record_data?.target_uri !== undefined,
            },
            {
                id: "restore",
                label: localize("Unarchive"),
                title: localize("Unarchive this history and move it back to your active histories"),
                icon: faUndo,
                variant: !history.value.purged ? "primary" : "outline-primary",
                handler: () => onRestoreHistory(history.value),
                visible: archivedView,
            },
            {
                id: "view",
                label: localize("View"),
                title: localize("View this history"),
                icon: faEye,
                variant: "primary",
                to: `/histories/view?id=${history.value.id}`,
            },
        ];
    });

    return { historyCardExtraActions, historyCardSecondaryActions, historyCardPrimaryActions };
}
