<script setup lang="ts">
/**
 * HistoryCard Component
 *
 * A generic card component for displaying individual history entries.
 * This component handles the presentation and interaction logic for a single history item,
 * supporting various view modes and contexts within the application.
 *
 * Features:
 * - Displays history metadata (name, annotation, tags, update time)
 * - Supports different view contexts (my, shared, published, archived)
 * - Handles history selection for bulk operations
 * - Provides action menus for history management
 * - Shows visual indicators (published, shared, deleted states)
 * - Enables tag editing and filtering
 * - Responsive layout for grid and list views
 * - Export record DOI links for archived histories
 * - Dataset count badges
 *
 * @component HistoryCard
 * @example
 * <HistoryCard
 *   :history="historyItem"
 *   :grid-view="true"
 *   :selectable="true"
 *   @select="onHistorySelect"
 *   @tagClick="onTagFilter" />
 */

import { storeToRefs } from "pinia";
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import { userOwnsHistory } from "@/api";
import type { AnyHistoryEntry } from "@/api/histories";
import { isArchivedHistory, isMyHistory } from "@/api/histories";
import { useHistoryCardActions } from "@/components/History/useHistoryCardActions";
import { useHistoryCardBadges } from "@/components/History/useHistoryCardBadges";
import { useHistoryCardIndicators } from "@/components/History/useHistoryCardIndicators";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";

import ExportRecordDOILink from "@/components/Common/ExportRecordDOILink.vue";
import GCard from "@/components/Common/GCard.vue";
import HistoryDatasetsBadge from "@/components/History/HistoryDatasetsBadge.vue";

interface Props {
    /**
     * The history entry data to display
     * @type {AnyHistoryEntry}
     */
    history: AnyHistoryEntry;

    /**
     * Whether this card is in the archived histories view
     * @type {boolean}
     * @default false
     */
    archivedView?: boolean;

    /**
     * Whether to display in grid view mode (vs list view)
     * @type {boolean}
     * @default false
     */
    gridView?: boolean;

    /**
     * Whether this card is in the published histories view
     * @type {boolean}
     * @default false
     */
    publishedView?: boolean;

    /**
     * Whether this history can be selected for bulk operations
     * @type {boolean}
     * @default false
     */
    selectable?: boolean;

    /**
     * Whether this history is currently selected
     * @type {boolean}
     * @default false
     */
    selected?: boolean;

    /**
     * Whether this card is in the shared histories view
     * @type {boolean}
     * @default false
     */
    sharedView?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    archivedView: false,
    gridView: false,
    publishedView: false,
    selectable: false,
    selected: false,
    sharedView: false,
});

const router = useRouter();

const historyStore = useHistoryStore();

const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);

/**
 * Events emitted to parent components
 */
const emit = defineEmits<{
    /**
     * Emitted when this history is selected for bulk operations
     * @event select
     */
    (e: "select", history: AnyHistoryEntry): void;

    /**
     * Emitted when the history title is clicked
     * @event titleClick
     */
    (e: "titleClick", history: AnyHistoryEntry["id"]): void;

    /**
     * Emitted when a tag is clicked for filtering
     * @event tagClick
     */
    (e: "tagClick", tag: string): void;

    /**
     * Emitted when the parent list needs to be refreshed
     * @event refreshList
     */
    (e: "refreshList", overlayLoading?: boolean, silent?: boolean): void;

    /**
     * Emitted when a filter value needs to be updated
     * @event updateFilter
     */
    (e: "updateFilter", key: string, value: any): void;
}>();

/**
 * Handles clicking on the history title to navigate to the history view
 * @function onTitleClick
 */
function onTitleClick() {
    router.push(`/histories/view?id=${props.history.id}`);
}

/**
 * Computed property that creates the title configuration for the history card
 * @returns {Object} Title configuration with label, tooltip, and click handler
 */
const historyCardTitle = computed(() => {
    return {
        label: props.history.name,
        title: localize("Click to view this history"),
        handler: onTitleClick,
    };
});

/**
 * Get action configurations for the history card
 */
const { historyCardExtraActions, historyCardSecondaryActions, historyCardPrimaryActions } = useHistoryCardActions(
    computed(() => props.history),
    props.archivedView,
    () => emit("refreshList", true)
);

/**
 * Get visual indicators for the history card
 */
const { historyCardIndicators } = useHistoryCardIndicators(
    computed(() => props.history),
    props.archivedView,
    (k, v) => emit("updateFilter", k, v)
);

/**
 * Get title badges for the history card
 */
const { historyCardTitleBadges } = useHistoryCardBadges(
    computed(() => props.history),
    props.sharedView,
    props.publishedView,
    (k, v) => emit("updateFilter", k, v)
);

/**
 * Handles updating tags for a history
 * @param {string} historyId - The ID of the history to update
 * @param {string[]} tags - The new array of tags to set
 */
async function onTagsUpdate(historyId: string, tags: string[]) {
    await historyStore.updateHistory(historyId, { tags: tags });
    emit("refreshList", true, true);
}
</script>

<template>
    <GCard
        :id="`history-${history.id}`"
        :key="history.id"
        :title="historyCardTitle"
        :title-badges="historyCardTitleBadges"
        :title-n-lines="2"
        :can-rename-title="!history.deleted && !history.purged && isMyHistory(history)"
        :description="history.annotation || ''"
        :grid-view="props.gridView"
        :indicators="historyCardIndicators"
        :extra-actions="historyCardExtraActions"
        :primary-actions="historyCardPrimaryActions"
        :secondary-actions="historyCardSecondaryActions"
        :published="history.published"
        :selectable="props.selectable"
        :selected="props.selected"
        :tags="history.tags"
        :tags-editable="userOwnsHistory(currentUser, history)"
        :max-visible-tags="props.gridView ? 2 : 8"
        :update-time="history.update_time"
        @titleClick="onTitleClick"
        @rename="() => router.push(`/histories/rename?id=${history.id}`)"
        @select="isMyHistory(history) && emit('select', history)"
        @tagsUpdate="(tags) => onTagsUpdate(history.id, tags)"
        @tagClick="(tag) => emit('tagClick', tag)">
        <template v-if="props.archivedView && isArchivedHistory(history)" v-slot:titleActions>
            <ExportRecordDOILink :export-record-uri="history.export_record_data?.target_uri" />
        </template>

        <template v-slot:badges>
            <HistoryDatasetsBadge :history-id="history.id" :count="history.count" />
        </template>
    </GCard>
</template>
