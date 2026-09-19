<script setup lang="ts">
import { ref } from "vue";

import type { SearchData } from "@/stores/workflowSearchStore";

import GraphSearch from "../Workflow/GraphSearch.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";

const currentQuery = ref("");

const emit = defineEmits<{
    (e: "result-clicked", result: SearchData): void;
}>();
</script>

<template>
    <ActivityPanel title="Search">
        <DelayedInput placeholder="search workflow" :delay="200" @change="(v) => (currentQuery = v)" />

        <GraphSearch :current-query="currentQuery" @result-clicked="(result) => emit('result-clicked', result)" />
    </ActivityPanel>
</template>
