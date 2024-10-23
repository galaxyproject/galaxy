<script setup lang="ts">
interface Props {
    initialFilterText: string;
    clientMode: string;
}

defineProps<Props>()

import WorkflowList from "@/components/Workflow/WorkflowList.vue";
</script>

<template>
    <div>
        <WorkflowList active-list="published" :client-mode="clientMode" :initial-filter-text="initialFilterText" />
    </div>
</template>
