<script setup lang="ts">
import GAlert from "@/components/BaseComponents/GAlert.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

withDefaults(
    defineProps<{
        error?: string | null;
        loading: boolean;
        /** The number of nodes in the graph */
        nodeCount: number;
        /** The number of tool execution nodes in the graph */
        executionCount: number;
        /** Shown when the history is empty */
        emptyMessage?: string;
    }>(),
    {
        error: null,
        emptyMessage: "This history is empty.",
    },
);
</script>

<template>
    <GAlert v-if="error" variant="danger" show>{{ error }}</GAlert>
    <LoadingSpan v-else-if="loading" message="Loading history graph" />
    <GAlert v-else-if="nodeCount === 0" show variant="info" class="m-3">{{ emptyMessage }}</GAlert>
    <GAlert v-else-if="executionCount === 0" show variant="info" class="m-3">
        No History Graph available. Please ensure that the History contains tool executions, and note that Galaxy
        started capturing the required tool execution data with release 26.1.
    </GAlert>
    <slot v-else />
</template>
