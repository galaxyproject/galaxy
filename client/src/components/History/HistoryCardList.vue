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

import type { Ref } from "vue";

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

    /**
     * Whether cards are clickable for navigation
     * @type {boolean}
     * @default false
     */
    clickable?: boolean;

    /**
     * Item refs for keyboard navigation
     * @type {Record<string, Ref<InstanceType<typeof HistoryCard> | null>>}
     * @default {}
     */
    itemRefs?: Record<string, Ref<InstanceType<typeof HistoryCard> | null>>;

    /**
     * Range select anchor for keyboard navigation
     * @type {AnyHistoryEntry | undefined}
     */
    rangeSelectAnchor?: AnyHistoryEntry;
}

const props = withDefaults(defineProps<Props>(), {
    gridView: false,
    publishedView: false,
    selectable: false,
    selectedHistoryIds: () => [],
    clickable: false,
    itemRefs: () => ({}),
    rangeSelectAnchor: undefined,
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

    /**
     * Emitted when a keyboard event occurs on a history card
     * @event on-key-down
     */
    (e: "on-key-down", history: AnyHistoryEntry, event: KeyboardEvent): void;

    /**
     * Emitted when a history card is clicked
     * @event on-history-card-click
     */
    (e: "on-history-card-click", history: AnyHistoryEntry, event: Event): void;
}>();
</script>

<template>
    <div class="history-card-list d-flex flex-wrap overflow-auto pt-1">
        <HistoryCard
            v-for="history in props.histories"
            :ref="props.itemRefs[history.id]"
            :key="history.id"
            tabindex="0"
            :history="history"
            :grid-view="props.gridView"
            :shared-view="props.sharedView"
            :published-view="props.publishedView"
            :archived-view="props.archivedView"
            :selectable="props.selectable"
            :selected="props.selectedHistoryIds.some((selected) => selected.id === history.id)"
            :clickable="props.clickable"
            :highlighted="props.rangeSelectAnchor?.id === history.id"
            class="history-card-in-list"
            @select="isMyHistory(history) && emit('select', history)"
            @tagClick="(...args) => emit('tagClick', ...args)"
            @refreshList="(...args) => emit('refreshList', ...args)"
            @updateFilter="(...args) => emit('updateFilter', ...args)"
            @on-key-down="(...args) => emit('on-key-down', ...args)"
            @on-history-card-click="(...args) => emit('on-history-card-click', ...args)" />
    </div>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";

.history-card-list {
    container: cards-list / inline-size;
}
</style>
