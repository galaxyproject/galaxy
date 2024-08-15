<script setup lang="ts">
import { storeToRefs } from "pinia";
import { ref } from "vue";

import type { CollectionEntry } from "@/api";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import CurrentCollection from "@/components/History/CurrentCollection/CollectionPanel.vue";
import HistoryNavigation from "@/components/History/CurrentHistory/HistoryNavigation.vue";
import HistoryPanel from "@/components/History/CurrentHistory/HistoryPanel.vue";

const userStore = useUserStore();
const historyStore = useHistoryStore();

const { currentUser } = storeToRefs(userStore);
const { currentHistory, histories, historiesLoading } = storeToRefs(historyStore);

const listOffset = ref<number | undefined>(0);
const breadcrumbs = ref<CollectionEntry[]>([]);

function onViewCollection(collection: CollectionEntry, currentOffset?: number) {
    listOffset.value = currentOffset;
    breadcrumbs.value = [...breadcrumbs.value, collection];
}
</script>

<template>
    <div
        v-if="currentUser && currentHistory"
        id="current-history-panel"
        class="d-flex flex-column history-index overflow-auto">
        <HistoryPanel
            v-if="!breadcrumbs.length"
            :list-offset="listOffset"
            :history="currentHistory"
            :filterable="true"
            @view-collection="onViewCollection">
            <template v-slot:navigation>
                <HistoryNavigation
                    :history="currentHistory"
                    :histories="histories"
                    :histories-loading="historiesLoading" />
            </template>
        </HistoryPanel>

        <CurrentCollection
            v-else-if="breadcrumbs.length"
            :history="currentHistory"
            :selected-collections.sync="breadcrumbs"
            @view-collection="onViewCollection" />

        <div v-else>
            <span class="sr-only">Loading...</span>
        </div>
    </div>

    <div v-else class="flex-grow-1 loadingBackground h-100">
        <span v-localize class="sr-only">Loading History...</span>
    </div>
</template>
