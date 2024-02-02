<script setup lang="ts">
import { onMounted, ref } from "vue";

import { historyFetcher } from "@/api/histories";

import PublishedItem from "@/components/Common/PublishedItem.vue";
import HistoryView from "@/components/History/HistoryView.vue";

interface Props {
    id: string;
}

const props = defineProps<Props>();
const history = ref({});

onMounted(async () => {
    const result = await historyFetcher({ history_id: props.id });

    history.value = result;
});
</script>

<template>
    <PublishedItem :item="history">
        <template v-slot>
            <HistoryView :id="id" />
        </template>
    </PublishedItem>
</template>
