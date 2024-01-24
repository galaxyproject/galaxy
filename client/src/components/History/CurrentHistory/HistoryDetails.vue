<script setup lang="ts">
import type { HistorySummary } from "@/api";
import { useHistoryStore } from "@/stores/historyStore";

import DetailsLayout from "@/components/History/Layout/DetailsLayout.vue";

interface Props {
    history: HistorySummary;
    writeable: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    writeable: true,
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
        @save="onSave">
        <template v-slot:name>
            <!-- eslint-disable-next-line vuejs-accessibility/heading-has-content -->
            <h3 v-short="history.name || 'History'" data-description="name display" class="my-2" />
        </template>
    </DetailsLayout>
</template>
