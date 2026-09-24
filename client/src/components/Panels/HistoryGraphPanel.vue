<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import type { HistorySummary } from "@/api";
import { HistoriesFilters } from "@/components/History/HistoriesFilters";
import { useHistoryStore } from "@/stores/historyStore";

import ActivityPanel from "./ActivityPanel.vue";
import FilterMenu from "@/components/Common/FilterMenu.vue";
import HistoryScrollList from "@/components/History/HistoryScrollList.vue";

const route = useRoute();
const router = useRouter();

const filter = ref("");
const showAdvanced = ref(false);
const loading = ref(false);

const { historiesLoading } = storeToRefs(useHistoryStore());

// Highlight the row whose graph is currently open in the centre panel — the
// route's `historyId` param when sitting on /histories/:historyId/graph. Pass
// `null` (no match) when off that route so no row is highlighted, instead of
// falling back to the store's currentHistoryId.
const highlightId = computed(() => (route.params.historyId as string | undefined) ?? null);

function setFilter(newFilter: string, newValue: string) {
    filter.value = HistoriesFilters.setFilterValue(filter.value, newFilter, newValue);
}

function openGraph(history: HistorySummary) {
    router.push(`/histories/${history.id}/graph`);
}
</script>

<template>
    <ActivityPanel title="History Graphs">
        <template v-slot:header>
            <FilterMenu
                name="Histories"
                placeholder="search histories"
                :filter-class="HistoriesFilters"
                :filter-text.sync="filter"
                :loading="historiesLoading || loading"
                :show-advanced.sync="showAdvanced" />
        </template>
        <HistoryScrollList
            v-show="!showAdvanced"
            :filter="filter"
            :loading.sync="loading"
            :current-item-id="highlightId"
            hide-deleted
            @setFilter="setFilter"
            @selectHistory="openGraph" />
    </ActivityPanel>
</template>
