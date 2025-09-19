import {
    faBurn,
    faCopy,
    faExchangeAlt,
    faEye,
    faTrash,
    faTrashRestore,
    faUndo,
    faUsersCog,
} from "@fortawesome/free-solid-svg-icons";
import type { ComputedRef, Ref } from "vue";
import { computed } from "vue";

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

/**
 * Custom Vue composable for managing history card actions
 *
 * This composable provides action configurations for history cards, including
 * delete, restore, share, import, and navigation actions.
 * It handles the logic for each action and returns properly configured action
 * objects for use with the GCard component.
 *
 * @param {Ref<AnyHistoryEntry>} history - Reactive reference to the history entry
 * @param {boolean} archivedView - Whether the card is displayed in archived view
 * @param {() => void} refreshCallBack - Callback function to refresh the parent list
 * @returns {Object} Object containing action arrays for different action categories
 *
 * @example
 * const { historyCardExtraActions, historyCardSecondaryActions, historyCardPrimaryActions } =
 *   useHistoryCardActions(historyRef, false, () => refreshList());
 */
export function useHistoryCardActions(
    history: Ref<AnyHistoryEntry>,
    archivedView: boolean,
    refreshCallBack: () => void,
): {
    historyCardExtraActions: CardAction[];
    historyCardSecondaryActions: CardAction[];
    historyCardPrimaryActions: ComputedRef<CardAction[]>;
} {
    const { confirm } = useConfirmDialog();

    const historyStore = useHistoryStore();

    /**
     * Handles history deletion with optional permanent purge
     * Shows confirmation dialog and executes deletion via history store
     *
     * @param {boolean} purge - Whether to permanently delete (purge) the history
     */
    async function onDeleteHistory(purge: boolean = false) {
        const confirmed = await confirm(
            `Are you sure you want to ${purge ? "permanently delete" : "delete"} this history?`,
            {
                id: "delete-history",
                title: purge ? "Permanently Delete History" : "Delete History",
                okTitle: purge ? "Permanently Delete" : "Delete",
                okVariant: "danger",
                cancelVariant: "outline-primary",
                centered: true,
            },
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

    /**
     * Handles restoration of a deleted history
     * Executes restoration via history store and shows success/error messages
     */
    async function onRestore() {
        try {
            await historyStore.restoreHistory(history.value.id);
            refreshCallBack();
            Toast.success("History restored");
        } catch (e) {
            Toast.error(`Failed to restore history: ${errorMessageAsString(e)}`);
        }
    }

    /**
     * Handles importing a copy of an archived history from its export record
     * Shows confirmation dialog and creates a new history from the export snapshot
     *
     * @param {ArchivedHistorySummary} hti - The archived history to import
     */
    async function onImportCopy(hti: ArchivedHistorySummary) {
        const confirmed = await confirm(
            localize(
                `Are you sure you want to import a new copy of this history? This will create a new history with the same datasets contained in the associated export snapshot.`,
            ),
            {
                id: "history-import-copy",
                title: localize(`Import Copy of '${hti.name}'?`),
            },
        );

        if (!confirmed) {
            return;
        }

        if (!hti.export_record_data) {
            Toast.error(
                localize(`Failed to import history '${hti.name}' because it does not have an export record.`),
                localize("History Import Failed"),
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
                localize("History Import Failed"),
            );
            return;
        }

        Toast.success(
            localize(
                `The History '${hti.name}' it's being imported. This process may take a while. Check your histories list after a few minutes.`,
            ),
            localize("Importing History in background..."),
        );
    }

    /**
     * Handles restoration of an archived history back to active histories
     * Shows different confirmation messages for purged vs non-purged histories
     *
     * @param {ArchivedHistorySummary} htr - The archived history to restore
     */
    async function onRestoreHistory(htr: ArchivedHistorySummary) {
        const confirmMessage =
            htr.purged && htr.export_record_data
                ? localize(
                      "Are you sure you want to restore this (purged) history? Please note that this will not restore the datasets associated with this history. If you want to fully recover it, you can import a copy from the export record instead.",
                  )
                : localize(
                      "Are you sure you want to restore this history? This will move the history back to your active histories.",
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
                localize("History Restore Failed"),
            );
        }
    }

    /**
     * Extra actions shown in the history card dropdown menu
     * Includes destructive actions like delete and purge
     * @type {CardAction[]}
     */
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

    /**
     * Secondary actions shown as buttons on the history card
     * Includes sharing and access management action
     * @type {CardAction[]}
     */
    const historyCardSecondaryActions: CardAction[] = [
        {
            id: "share-access-management",
            label: localize("Share & Manage Access"),
            title: localize("Share, Publish, or Set Permissions for this History"),
            icon: faUsersCog,
            variant: "outline-primary",
            to: `/histories/sharing?id=${history.value.id}`,
            visible: !history.value.deleted && isMyHistory(history.value),
        },
    ];

    /**
     * Primary actions computed dynamically based on history state
     * Includes restore, switch current, import copy, unarchive, and view actions
     * Actions are shown/hidden based on history state and context
     * @type {ComputedRef<CardAction[]>}
     */
    const historyCardPrimaryActions: ComputedRef<CardAction[]> = computed(() => {
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
