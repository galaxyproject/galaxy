<script setup lang="ts">
/**
 * HistoryCardList Component
 *
 * A container component that renders a collection of history items as cards.
 * This component serves as a bridge between the parent HistoryList component
 * and individual HistoryCard components, handling the layout and event delegation.
 *
 * Features:
 * - Displays histories in either grid or list view mode
 * - Supports different view contexts (my, shared, published, archived)
 * - Handles history selection for bulk operations
 * - Delegates events from individual cards to parent components
 * - Responsive card layout using CSS container queries
 *
 * @component HistoryCardList
 * @example
 * <HistoryCardList
 *   :histories="historyItems"
 *   :grid-view="true"
 *   :selectable="true"
 *   @select="onHistorySelect"
 *   @tagClick="onTagClick" />
 */

import type { AnyHistoryEntry, MyHistory } from "@/api/histories";
import { isMyHistory } from "@/api/histories";

import HistoryCard from "@/components/History/HistoryCard.vue";

interface Props {
    /**
     * Array of history entries to display
     * @type {AnyHistoryEntry[]}
     */
    histories: AnyHistoryEntry[];

    /**
     * Whether to display histories in grid view mode (default: false for list view)
     * @type {boolean}
     * @default false
     */
    gridView?: boolean;

    /**
     * Whether this is the published histories view
     * @type {boolean}
     * @default false
     */
    publishedView?: boolean;

    /**
     * Whether this is the archived histories view
     * @type {boolean}
     * @default false
     */
    archivedView?: boolean;

    /**
     * Whether this is the shared histories view
     * @type {boolean}
     * @default false
     */
    sharedView?: boolean;

    /**
     * Whether individual histories can be selected for bulk operations
     * @type {boolean}
     * @default false
     */
    selectable?: boolean;

    /**
     * Array of currently selected history IDs
     * @type {{ id: string }[]}
     * @default []
     */
    selectedHistoryIds?: { id: string }[];
}

const props = withDefaults(defineProps<Props>(), {
    gridView: false,
    publishedView: false,
    selectable: false,
    selectedHistoryIds: () => [],
});

/**
 * Events emitted to parent components
 */
const emit = defineEmits<{
    /**
     * Emitted when a history item is selected for bulk operations
     * @event select
     */
    (e: "select", history: MyHistory): void;

    /**
     * Emitted when a tag is clicked on a history card
     * @event tagClick
     */
    (e: "tagClick", tag: string): void;

    /**
     * Emitted when the history list needs to be refreshed
     * @event refreshList
     */
    (e: "refreshList", overlayLoading?: boolean, silent?: boolean): void;

    /**
     * Emitted when a filter needs to be updated
     * @event updateFilter
     */
    (e: "updateFilter", key: string, value: any): void;
}>();
</script>

<template>
    <div class="history-card-list d-flex flex-wrap overflow-auto">
        <HistoryCard
            v-for="history in props.histories"
            :key="history.id"
            :history="history"
            :grid-view="props.gridView"
            :shared-view="props.sharedView"
            :published-view="props.publishedView"
            :archived-view="props.archivedView"
            :selectable="props.selectable"
            :selected="props.selectedHistoryIds.some((selected) => selected.id === history.id)"
            @select="isMyHistory(history) && emit('select', history)"
            @tagClick="(...args) => emit('tagClick', ...args)"
            @refreshList="(...args) => emit('refreshList', ...args)"
            @updateFilter="(...args) => emit('updateFilter', ...args)" />
    </div>
</template>

<style lang="scss" scoped>
.history-card-list {
    container: cards-list / inline-size;
}
</style>
