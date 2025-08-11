<script setup lang="ts">
import {
    faBurn,
    faCopy,
    faExchangeAlt,
    faEye,
    faGlobe,
    faShareAlt,
    faTrash,
    faTrashRestore,
    faUndo,
    faUser,
    faUsers,
} from "@fortawesome/free-solid-svg-icons";
import { storeToRefs } from "pinia";
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import { GalaxyApi } from "@/api";
import type { AnyHistoryEntry, MyHistory, PublishedHistory, SharedHistory } from "@/api/histories";
import type { ArchivedHistorySummary } from "@/api/histories.archived";
import type { CardAction, CardBadge } from "@/components/Common/GCard.types";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { Toast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import ExportRecordDOILink from "@/components/Common/ExportRecordDOILink.vue";
import GCard from "@/components/Common/GCard.vue";
import HistoryDatasetsBadge from "@/components/History/HistoryDatasetsBadge.vue";

interface Props {
    histories: AnyHistoryEntry[];
    gridView?: boolean;
    publishedView?: boolean;
    archivedView?: boolean;
    sharedView?: boolean;
    selectable?: boolean;
    selectedHistoryIds?: { id: string }[];
}

const props = withDefaults(defineProps<Props>(), {
    gridView: false,
    publishedView: false,
    selectable: false,
    selectedHistoryIds: () => [],
});

const emit = defineEmits<{
    (e: "select", history: MyHistory): void;
    (e: "tagClick", tag: string): void;
    (e: "refreshList", overlayLoading?: boolean, silent?: boolean): void;
    (e: "updateFilter", key: string, value: any): void;
}>();

const router = useRouter();

const userStore = useUserStore();
const { isAnonymous } = storeToRefs(userStore);

const historyStore = useHistoryStore();

const { confirm } = useConfirmDialog();

const owned = computed(() => {
    return (username?: string) => userStore?.matchesCurrentUsername(username);
});
const isTagsEditable = computed(() => {
    return (history: AnyHistoryEntry) => !isAnonymous.value && !history.deleted && isMyHistory(history);
});

function isMyHistory(history: AnyHistoryEntry): history is MyHistory {
    return "username" in history && owned.value(history.username);
}

function isSharedHistory(history: AnyHistoryEntry): history is SharedHistory {
    return "username" in history && !owned.value(history.username);
}

function isPublishedHistory(history: AnyHistoryEntry): history is PublishedHistory {
    return "published" in history && history.published;
}

function isArchivedHistory(history: AnyHistoryEntry): history is ArchivedHistorySummary {
    return "archived" in history && history.archived;
}

function onTitleClick(historyId: string) {
    router.push(`/histories/view?id=${historyId}`);
}

function onRename(historyId: string) {
    router.push(`/histories/rename?id=${historyId}`);
}

async function onTagsUpdate(historyId: string, tags: string[]) {
    await historyStore.updateHistory(historyId, { tags: tags });
    emit("refreshList", true, true);
}

async function onDeleteHistory(historyId: string, purge = false) {
    const confirmed = await confirm(
        `Are you sure you want to ${purge ? "permanently delete" : "delete"} this history?`,
        {
            title: purge ? "Permanently Delete History" : "Delete History",
            okTitle: purge ? "Permanently Delete" : "Delete",
            okVariant: "danger",
            cancelVariant: "outline-primary",
            centered: true,
        }
    );

    if (confirmed) {
        try {
            await historyStore.deleteHistory(String(historyId), purge);
            Toast.success("History deleted");
        } catch (e) {
            Toast.error(`Failed to delete history: ${errorMessageAsString(e)}`);
        }
    }
}

async function onRestore(historyId: string) {
    try {
        await historyStore.restoreHistory(historyId);
        Toast.success("History restored");
        emit("refreshList", true, true);
    } catch (e) {
        Toast.error(`Failed to restore history: ${errorMessageAsString(e)}`);
    }
}

async function onRestoreHistory(history: ArchivedHistorySummary) {
    const confirmTitle = localize(`Unarchive '${history.name}'?`);
    const confirmMessage =
        history.purged && history.export_record_data
            ? localize(
                  "Are you sure you want to restore this (purged) history? Please note that this will not restore the datasets associated with this history. If you want to fully recover it, you can import a copy from the export record instead."
              )
            : localize(
                  "Are you sure you want to restore this history? This will move the history back to your active histories."
              );
    const confirmed = await confirm(confirmMessage, {
        title: confirmTitle,
        okTitle: "Unarchive",
        cancelVariant: "outline-primary",
        centered: true,
    });

    if (!confirmed) {
        return;
    }

    try {
        const force = true;
        await historyStore.unarchiveHistoryById(history.id, force);
        Toast.success(localize(`History '${history.name}' has been restored.`), localize("History Restored"));
        emit("refreshList", true, true);
    } catch (error) {
        Toast.error(
            localize(`Failed to restore history '${history.name}' with reason: ${error}`),
            localize("History Restore Failed")
        );
    }
}

async function onImportCopy(history: ArchivedHistorySummary) {
    const confirmed = await confirm(
        localize(
            `Are you sure you want to import a new copy of this history? This will create a new history with the same datasets contained in the associated export snapshot.`
        ),
        {
            title: localize(`Import Copy of '${history.name}'?`),
        }
    );
    if (!confirmed) {
        return;
    }

    if (!history.export_record_data) {
        Toast.error(
            localize(`Failed to import history '${history.name}' because it does not have an export record.`),
            localize("History Import Failed")
        );
        return;
    }

    const { error } = await GalaxyApi().POST("/api/histories/from_store_async", {
        body: {
            model_store_format: history.export_record_data?.model_store_format,
            store_content_uri: history.export_record_data?.target_uri,
        },
    });

    if (error) {
        Toast.error(
            localize(`Failed to import history '${history.name}' with reason: ${error}`),
            localize("History Import Failed")
        );
        return;
    }

    Toast.success(
        localize(
            `The History '${history.name}' it's being imported. This process may take a while. Check your histories list after a few minutes.`
        ),
        localize("Importing History in background...")
    );
}

function publishedIndicatorTitle(history: PublishedHistory): string {
    if (history.published && !props.publishedView) {
        return "Published history. Click to filter published histories";
    } else if (userStore.matchesCurrentUsername(history.username)) {
        return "Published by you";
    } else {
        return `Published by '${history.username}'`;
    }
}

function ownerBadgeTitle(history: SharedHistory | PublishedHistory): string {
    if (history.published && props.sharedView && !props.publishedView) {
        return `Shared by '${history.username}'. Click to view all histories shared by '${history.username}'`;
    } else if (userStore.matchesCurrentUsername(history.username)) {
        return "Published by you. Click to view all published histories by you";
    } else {
        return `Published by '${history.username}'. Click to view all published histories by '${history.username}'`;
    }
}

function getIndicators(history: AnyHistoryEntry): CardBadge[] {
    const cardIndicators: CardBadge[] = [
        {
            id: "deleted",
            label: "",
            title: "This history has been deleted.",
            icon: faTrash,
            disabled: props.publishedView,
            visible: history.deleted && !history.purged,
        },
        {
            id: "purged",
            label: "",
            title: "This history has been permanently deleted",
            icon: faBurn,
            variant: "danger",
            disabled: props.publishedView,
            visible: history.purged,
        },
    ];

    if (isPublishedHistory(history)) {
        cardIndicators.push({
            id: "published",
            label: "",
            title: publishedIndicatorTitle(history),
            icon: faGlobe,
            handler: () => emit("updateFilter", "published", true),
            disabled: props.publishedView,
            visible: true,
        });
    }

    return cardIndicators;
}

function getExtraActions(history: AnyHistoryEntry): CardAction[] {
    return [
        {
            id: "delete",
            label: "Delete",
            title: "Delete this history",
            icon: faTrash,
            handler: () => onDeleteHistory(history.id),
            visible: !history.deleted && isMyHistory(history),
        },
        {
            id: "purge",
            label: "Delete Permanently",
            title: "Purge this history (permanently delete)",
            icon: faBurn,
            handler: () => onDeleteHistory(history.id, true),
            visible: !history.purged && isMyHistory(history),
        },
    ];
}

function getHistoryTitleBadges(history: AnyHistoryEntry): CardBadge[] {
    const historyCardBadges: CardBadge[] = [
        {
            id: "snapshot",
            label: "Snapshot available",
            title: "This history has an associated export record containing a snapshot of the history that can be used to import a copy of the history.",
            icon: faCopy,
            visible: isArchivedHistory(history) && !!history.export_record_data,
        },
    ];

    if (isSharedHistory(history)) {
        historyCardBadges.unshift({
            id: "owner-shared",
            label: history.username,
            title: `'${history.username}' shared this history with you. Click to view all histories shared with you by '${history.username}'`,
            icon: faUsers,
            type: "badge",
            variant: "outline-secondary",
            handler: () => emit("updateFilter", "user", history.username),
            visible: !owned.value(history.username) && props.sharedView,
        });
    }

    if (isPublishedHistory(history)) {
        historyCardBadges.unshift({
            id: "owner-published",
            label: history.username,
            title: ownerBadgeTitle(history),
            icon: faUser,
            type: "badge",
            variant: "outline-secondary",
            disabled: props.publishedView,
            handler: () => emit("updateFilter", "user", history.username),
            visible: props.publishedView,
        });
    }

    return historyCardBadges;
}

function getPrimaryActions(
    history: MyHistory | PublishedHistory | SharedHistory | ArchivedHistorySummary
): CardAction[] {
    return [
        {
            id: "restore",
            title: "Restore this history",
            label: "Restore",
            variant: "outline-primary",
            icon: faTrashRestore,
            handler: () => onRestore(history.id),
            visible: history.deleted && !history.purged && isMyHistory(history),
        },
        {
            id: "switch",
            title: "Set as current history",
            label: "Set as Current",
            variant: "outline-primary",
            icon: faExchangeAlt,
            handler: () => historyStore.setCurrentHistory(String(history.id)),
            visible: (isMyHistory(history) || props.archivedView) && historyStore.currentHistoryId !== history.id,
        },
        {
            title: "current history",
            id: "current",
            label: "Current",
            variant: "outline-primary",
            disabled: true,
            visible: (isMyHistory(history) || props.archivedView) && historyStore.currentHistoryId === history.id,
        },
        {
            id: "import-copy",
            label: "Import Copy",
            icon: faCopy,
            title: "Import a new copy of this history from the associated export record",
            disabled: isArchivedHistory(history) && history.export_record_data?.target_uri === undefined,
            variant: history.purged ? "primary" : "outline-primary",
            handler: () => onImportCopy(history),
            visible: isArchivedHistory(history) && history.export_record_data?.target_uri !== undefined,
        },
        {
            id: "restore",
            label: "Unarchive",
            icon: faUndo,
            title: "Unarchive this history and move it back to your active histories",
            variant: !history.purged ? "primary" : "outline-primary",
            handler: () => onRestoreHistory(history),
            visible: props.archivedView,
        },
        {
            id: "view",
            label: "View",
            title: "View this history",
            icon: faEye,
            variant: "primary",
            to: `/histories/view?id=${history.id}`,
        },
    ];
}

function getSecondaryActions(history: AnyHistoryEntry): CardAction[] {
    return [
        {
            id: "change-permissions",
            label: "Change Permissions",
            title: "Change permissions for this history",
            icon: faUsers,
            to: `/histories/permissions?id=${history.id}`,
            visible: !history.deleted && isMyHistory(history),
        },
        {
            id: "share",
            label: "Share",
            title: "Share this history",
            icon: faShareAlt,
            variant: "outline-primary",
            to: `/histories/sharing?id=${history.id}`,
            visible: !history.deleted && isMyHistory(history),
        },
    ];
}
</script>

<template>
    <div class="history-card-list d-flex flex-wrap overflow-auto">
        <GCard
            v-for="history in props.histories"
            :id="`history-${history.id}`"
            :key="history.id"
            :title="{
                label: history.name,
                title: 'Click to view this history',
                handler: () => onTitleClick(history.id),
            }"
            :title-badges="getHistoryTitleBadges(history)"
            :title-n-lines="2"
            :primary-actions="getPrimaryActions(history)"
            :secondary-actions="getSecondaryActions(history)"
            :extra-actions="getExtraActions(history)"
            :indicators="getIndicators(history)"
            :selectable="props.selectable"
            :selected="props.selectedHistoryIds.some((selected) => selected.id === history.id)"
            :grid-view="props.gridView"
            :description="history.annotation || ''"
            :published="history.published"
            :tags="history.tags"
            :update-time="history.update_time"
            :tags-editable="isTagsEditable(history)"
            :max-visible-tags="props.gridView ? 2 : 8"
            :can-rename-title="!history.deleted && !history.purged && isMyHistory(history)"
            @rename="() => onRename(history.id)"
            @select="isMyHistory(history) && emit('select', history)"
            @titleClick="() => onTitleClick(history.id)"
            @tagsUpdate="(tags) => onTagsUpdate(history.id, tags)"
            @tagClick="(tag) => emit('tagClick', tag)">
            <template v-if="props.archivedView && isArchivedHistory(history)" v-slot:titleActions>
                <ExportRecordDOILink :export-record-uri="history.export_record_data?.target_uri" />
            </template>

            <template v-slot:badges>
                <HistoryDatasetsBadge :history-id="history.id" :count="history.count" />
            </template>
        </GCard>
    </div>
</template>

<style lang="scss" scoped>
.history-card-list {
    container: cards-list / inline-size;
}
</style>
