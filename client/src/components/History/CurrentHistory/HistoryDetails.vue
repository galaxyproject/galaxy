<script setup lang="ts">
import { BBadge } from "bootstrap-vue";

import type { HistorySummary } from "@/api";
import { useHistoryStore } from "@/stores/historyStore";

import TextSummary from "@/components/Common/TextSummary.vue";
import DetailsLayout from "@/components/History/Layout/DetailsLayout.vue";
import UtcDate from "@/components/UtcDate.vue";

interface Props {
    history: HistorySummary;
    writeable: boolean;
    summarized?: "both" | "annotation" | "tags" | "none";
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
            <BBadge v-b-tooltip pill>
                <span v-localize>last edited </span>
                <UtcDate v-if="history.update_time" :date="history.update_time" mode="elapsed" />
            </BBadge>
        </template>
    </DetailsLayout>
</template>
