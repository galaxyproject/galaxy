<script setup lang="ts">
import type { HistorySummary } from "@/api";
import { useConfig } from "@/composables/config";
import { useHistoryStore } from "@/stores/historyStore";

import type { DetailsLayoutSummarized } from "../Layout/types";

import HistoryIndicators from "../HistoryIndicators.vue";
import StorageLocationIndicator from "./StorageLocationIndicator.vue";
import DetailsLayout from "@/components/History/Layout/DetailsLayout.vue";

interface Props {
    history: HistorySummary;
    writeable: boolean;
    summarized?: DetailsLayoutSummarized;
}

const props = withDefaults(defineProps<Props>(), {
    writeable: true,
    summarized: undefined,
});

const historyStore = useHistoryStore();

function onSave(newDetails: HistorySummary) {
    const id = props.history.id;
    historyStore.updateHistory(id, { ...newDetails });
}

const { config } = useConfig();
</script>

<template>
    <DetailsLayout
        :name="history.name"
        :annotation="history.annotation || ''"
        :tags="history.tags"
        :writeable="writeable"
        :summarized="summarized"
        :update-time="history.update_time"
        @save="onSave">
        <template v-if="summarized" v-slot:update-time>
            <HistoryIndicators :history="history" detailed-time />
        </template>

        <StorageLocationIndicator v-if="config && config.object_store_allows_id_selection" :history="history" />
    </DetailsLayout>
</template>
