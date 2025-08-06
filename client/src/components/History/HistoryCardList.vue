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

import type { AnyHistory } from "@/api";
import { GalaxyApi } from "@/api";
import type { ArchivedHistorySummary } from "@/api/histories.archived";
import type { CardAction, CardBadge } from "@/components/Common/GCard.types";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { useToast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";

import ExportRecordDOILink from "@/components/Common/ExportRecordDOILink.vue";
import GCard from "@/components/Common/GCard.vue";
import HistoryDatasetsBadge from "@/components/History/HistoryDatasetsBadge.vue";

interface Props {
    histories: AnyHistory[];
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
    (e: "select", history: AnyHistory): void;
    (e: "tagClick", tag: string): void;
    (e: "refreshList", overlayLoading?: boolean, silent?: boolean): void;
    (e: "updateFilter", key: string, value: any): void;
}>();

const router = useRouter();

const userStore = useUserStore();
const { isAnonymous } = storeToRefs(userStore);

const historyStore = useHistoryStore();

const toast = useToast();
const { confirm } = useConfirmDialog();

const owned = computed(() => {
    return (username?: string) => userStore?.matchesCurrentUsername(username);
});
const isTagsEditable = computed(() => {
    return (history: AnyHistory) => !isAnonymous.value && !history.deleted && owned.value(history.username);
});

function onTitleClick(historyId: string) {
    router.push(`/histories/view?id=${historyId}`);
}

function onRename(historyId: string) {
    router.push(`/histories/rename?id=${historyId}`);
}

async function onTagsUpdate(historyId: string, tags: string[]) {
    const update = { tags: tags };
    await historyStore.updateHistory({ id: historyId, ...update });
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
            toast.success("History deleted");
        } catch (e) {
            toast.error("Failed to delete history");
        }
    }
}

async function onRestore(historyId: string) {
    try {
        await historyStore.restoreHistory(historyId);
        toast.success("History restored");
        emit("refreshList", true, true);
    } catch (e) {
        toast.error("Failed to restore history");
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
        toast.success(localize(`History '${history.name}' has been restored.`), localize("History Restored"));
        emit("refreshList", true, true);
    } catch (error) {
        toast.error(
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
        toast.error(
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
        toast.error(
            localize(`Failed to import history '${history.name}' with reason: ${error}`),
            localize("History Import Failed")
        );
        return;
    }

    toast.success(
        localize(
            `The History '${history.name}' it's being imported. This process may take a while. Check your histories list after a few minutes.`
        ),
        localize("Importing History in background...")
    );
}

function publishedIndicatorTitle(history: AnyHistory): string {
    if (history.published && !props.publishedView) {
        return "Published history. Click to filter published histories";
    } else if (userStore.matchesCurrentUsername(history.username)) {
        return "Published by you";
    } else {
        return `Published by '${history.username}'`;
    }
}

function ownerBadgeTitle(history: AnyHistory): string {
    if (history.published && props.sharedView && !props.publishedView) {
        return `Shared by '${history.username}'. Click to view all histories shared by '${history.username}'`;
    } else if (userStore.matchesCurrentUsername(history.username)) {
        return "Published by you. Click to view all published histories by you";
    } else {
        return `Published by '${history.username}'. Click to view all published histories by '${history.username}'`;
    }
}

function getIndicators(history: AnyHistory): CardBadge[] {
    return [
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
        {
            id: "published",
            label: "",
            title: publishedIndicatorTitle(history),
            icon: faGlobe,
            handler: () => emit("updateFilter", "published", true),
            disabled: props.publishedView,
            visible: history.published,
        },
    ];
}

function getExtraActions(history: AnyHistory): CardAction[] {
    return [
        {
            id: "delete",
            label: "Delete",
            title: "Delete this history",
            icon: faTrash,
            handler: () => onDeleteHistory(history.id),
            visible: !history.deleted && owned.value(history.username),
        },
        {
            id: "purge",
            label: "Delete Permanently",
            title: "Purge this history (permanently delete)",
            icon: faBurn,
            handler: () => onDeleteHistory(history.id, true),
            visible: !history.purged && owned.value(history.username),
        },
    ];
}

function getHistoryTitleBadges(history: AnyHistory): CardBadge[] {
    return [
        {
            id: "owner-shared",
            label: history.username,
            title: `'${history.username}' shared this history with you. Click to view all histories shared with you by '${history.username}'`,
            icon: faUsers,
            type: "badge",
            variant: "outline-secondary",
            handler: () => emit("updateFilter", "user", history.username),
            visible: !owned.value(history.username) && props.sharedView,
        },
        {
            id: "owner-published",
            label: history.username,
            title: () => ownerBadgeTitle(history),
            icon: faUser,
            type: "badge",
            variant: "outline-secondary",
            disabled: props.publishedView,
            handler: () => emit("updateFilter", "user", history.username),
            visible: history.published && props.publishedView,
        },
        {
            id: "snapshot",
            label: "Snapshot available",
            title: "This history has an associated export record containing a snapshot of the history that can be used to import a copy of the history.",
            icon: faCopy,
            visible: !!history.export_record_data,
        },
    ];
}

function getPrimaryActions(history: AnyHistory): CardAction[] {
    return [
        {
            id: "restore",
            title: "Restore this history",
            label: "Restore",
            variant: "outline-primary",
            icon: faTrashRestore,
            handler: () => onRestore(history.id),
            visible: history.deleted && !history.purged && owned.value(history.username),
        },
        {
            id: "switch",
            title: "Set as current history",
            label: "Set as Current",
            variant: "outline-primary",
            icon: faExchangeAlt,
            handler: () => historyStore.setCurrentHistory(String(history.id)),
            visible:
                (owned.value(history.username) || props.archivedView) && historyStore.currentHistoryId !== history.id,
        },
        {
            title: "current history",
            id: "current",
            label: "Current",
            variant: "outline-primary",
            disabled: true,
            visible:
                (owned.value(history.username) || props.archivedView) && historyStore.currentHistoryId === history.id,
        },
        {
            id: "import-copy",
            label: "Import Copy",
            icon: faCopy,
            title: "Import a new copy of this history from the associated export record",
            disabled: history.export_record_data?.target_uri === undefined,
            variant: history.purged ? "primary" : "outline-primary",
            handler: () => onImportCopy(history),
            visible: history.export_record_data?.target_uri !== undefined,
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

function getSecondaryActions(history: AnyHistory): CardAction[] {
    return [
        {
            id: "change-permissions",
            label: "Change Permissions",
            title: "Change permissions for this history",
            icon: faUsers,
            to: `/histories/permissions?id=${history.id}`,
            visible: !history.deleted && owned.value(history.username),
        },
        {
            id: "share",
            label: "Share",
            title: "Share this history",
            icon: faShareAlt,
            variant: "outline-primary",
            to: `/histories/sharing?id=${history.id}`,
            visible: !history.deleted && owned.value(history.username),
        },
    ];
}
</script>

<template>
    <div class="history-card-list d-flex flex-wrap overflow-auto">
        <GCard
            v-for="history in props.histories"
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
            :can-rename-title="!history.deleted && !history.purged && owned(history.username)"
            @rename="() => onRename(history.id)"
            @select="emit('select', history)"
            @titleClick="() => onTitleClick(history.id)"
            @tagsUpdate="(tags) => onTagsUpdate(history.id, tags)"
            @tagClick="(tag) => emit('tagClick', tag)">
            <template v-if="props.archivedView" v-slot:titleActions>
                <ExportRecordDOILink :export-record-uri="history.export_record_data?.target_uri" />
            </template>

            <template v-slot:badges>
                <HistoryDatasetsBadge
                    :history-id="history.id"
                    :count="history.count"
                    :nice-size="history.nice_size"
                    :contents-active="history.contents_active"
                    :contents-states="history.contents_states" />
            </template>
        </GCard>
    </div>
</template>

<style lang="scss" scoped>
.history-card-list {
    container: cards-list / inline-size;
}
</style>
