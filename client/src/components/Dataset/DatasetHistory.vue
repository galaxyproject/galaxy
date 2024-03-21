<script setup lang="ts">
import { computed } from "vue";

import { HDASummary } from "@/api/datasets";
import { useHistoryStore } from "@/stores/historyStore";

interface Props {
    item: HDASummary;
}

const props = defineProps<Props>();

const historyStore = useHistoryStore();

const historyName = computed(() => {
    return historyStore.getHistoryNameById(props.item.history_id);
});
</script>

<template>
    <div>
        {{ historyName }}
    </div>
</template>
