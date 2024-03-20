<script setup lang="ts">
import { computed } from "vue";

import { type components } from "@/api/schema";
import { useHistoryStore } from "@/stores/historyStore";

type HDASummary = components["schemas"]["HDASummary"];

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
