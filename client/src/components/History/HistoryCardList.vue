<script setup lang="ts">
import type { AnyHistoryEntry, MyHistory } from "@/api/histories";
import { isMyHistory } from "@/api/histories";

import HistoryCard from "@/components/History/HistoryCard.vue";

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
