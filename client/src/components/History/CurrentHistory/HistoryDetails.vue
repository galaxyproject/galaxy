<script setup lang="ts">
import type { HistorySummary } from "@/api";
import { useHistoryStore } from "@/stores/historyStore";

import type { DetailsLayoutSummarized } from "../Layout/types";

import HistoryIndicators from "../HistoryIndicators.vue";
import StorageLocationIndicator from "./StorageLocationIndicator.vue";
import TextSummary from "@/components/Common/TextSummary.vue";
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
    historyStore.updateHistory({ ...newDetails, id });
}
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
        <template v-slot:name>
            <!-- eslint-disable-next-line vuejs-accessibility/heading-has-content -->
            <h3 v-if="!summarized" v-short="history.name || 'History'" data-description="name display" class="my-2" />
            <TextSummary
                v-else
                :description="history.name"
                data-description="name display"
                class="my-2"
                component="h3"
                one-line-summary
                no-expand />
        </template>
        <template v-if="summarized" v-slot:update-time>
            <HistoryIndicators :history="history" detailed-time />
        </template>
        <!-- todo: check if object store feature active -->
        <StorageLocationIndicator />
    </DetailsLayout>
</template>
