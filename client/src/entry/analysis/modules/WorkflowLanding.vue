<script setup lang="ts">
interface Props {
    initialFilterText: string;
}

import WorkflowList from "@/components/Workflow/WorkflowList.vue";
</script>

<template>
    <div>
        <WorkflowList active-list="published" :advanced-options="false" :initial-filter-text="initialFilterText" />
    </div>
</template>
