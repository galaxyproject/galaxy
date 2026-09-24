<script setup lang="ts">
import { onMounted, ref } from "vue";

import { GalaxyApi, type HistoryDetailed } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

import PublishedItem from "@/components/Common/PublishedItem.vue";
import HistoryView from "@/components/History/HistoryView.vue";

interface Props {
    id: string;
}

const props = defineProps<Props>();
const history = ref<HistoryDetailed>();

onMounted(async () => {
    const { data, error } = await GalaxyApi().GET("/api/histories/{history_id}", {
        params: {
            path: { history_id: props.id },
        },
    });

    if (error) {
        rethrowSimple(error);
        return;
    }

    // The default view is the detailed view
    history.value = data as HistoryDetailed;
});
</script>

<template>
    <PublishedItem :item="history">
        <template v-slot>
            <HistoryView :id="id" />
        </template>
    </PublishedItem>
</template>
