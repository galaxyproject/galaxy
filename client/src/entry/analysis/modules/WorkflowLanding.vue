<script setup lang="ts">
import WorkflowList from "@/components/Workflow/List/WorkflowList.vue";

interface Props {
    initialFilterText: string;
    clientMode: string;
}

defineProps<Props>();
</script>

<template>
    <div>
        <WorkflowList active-list="published" :client-mode="clientMode" :initial-filter-text="initialFilterText" />
    </div>
</template>
