<script setup lang="ts">
import { computed } from "vue";

import { useHistoryStore } from "@/stores/historyStore";

import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import GridInvocation from "@/components/Grid/GridInvocation.vue";

interface HistoryInvocationProps {
    historyId: string;
}

const props = defineProps<HistoryInvocationProps>();

const historyStore = useHistoryStore();
const historyName = computed(() => historyStore.getHistoryNameById(props.historyId));

const breadcrumbItems = computed(() => [
    { title: "Histories", to: "/histories/list" },
    {
        title: historyName.value,
        to: `/histories/view?id=${props.historyId}`,
        superText: historyStore.currentHistoryId === props.historyId ? "current" : undefined,
    },
    { title: "Workflow Invocations" },
]);
</script>

<template>
    <div>
        <BreadcrumbHeading :items="breadcrumbItems" />

        <GridInvocation hide-heading :filtered-for="{ type: 'History', id: props.historyId, name: historyName }" />
    </div>
</template>
