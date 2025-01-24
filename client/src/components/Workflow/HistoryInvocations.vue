<script setup lang="ts">
import { computed } from "vue";

import { useHistoryStore } from "@/stores/historyStore";

import GridInvocation from "../Grid/GridInvocation.vue";

interface HistoryInvocationProps {
    historyId: string;
}

const props = defineProps<HistoryInvocationProps>();

const { getHistoryNameById } = useHistoryStore();
const historyName = computed(() => getHistoryNameById(props.historyId));
</script>
<template>
    <GridInvocation
        :filtered-for="{
            type: 'History',
            id: props.historyId,
            name: historyName,
        }" />
</template>
