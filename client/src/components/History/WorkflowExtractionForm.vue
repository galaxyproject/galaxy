<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed, ref } from "vue";

import { extractWorkflowFromHistory, type WorkflowExtractionSummary } from "@/api/histories";
import { useHistoryStore } from "@/stores/historyStore";
import { errorMessageAsString } from "@/utils/simple-error";

import BreadcrumbHeading from "../Common/BreadcrumbHeading.vue";
import LoadingSpan from "../LoadingSpan.vue";

const props = defineProps<{
    historyId: string;
}>();

const historyStore = useHistoryStore();
const historyName = computed(() => historyStore.getHistoryNameById(props.historyId));

const breadcrumbItems = computed(() => [
    { title: "Histories", to: "/histories/list" },
    {
        title: historyName.value,
        to: `/histories/view?id=${props.historyId}`,
        superText: historyStore.currentHistoryId === props.historyId ? "current" : undefined,
    },
    { title: "Extract Workflow" },
]);

const loading = ref(true);
const errorMessage = ref<string | null>(null);
const summary = ref<WorkflowExtractionSummary | null>(null);

extractWorkflow();

async function extractWorkflow() {
    try {
        summary.value = await extractWorkflowFromHistory(props.historyId);
    } catch (error) {
        errorMessage.value = errorMessageAsString(error);
    } finally {
        loading.value = false;
    }
}
</script>

<template>
    <div>
        <BreadcrumbHeading :items="breadcrumbItems" />

        <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
        <BAlert v-else-if="loading" variant="info" show>
            <LoadingSpan message="Extracting workflow from history" />
        </BAlert>

        <div v-else-if="summary">
            <!-- TODO: Implement full workflow extraction here -->
        </div>

        <BAlert v-else variant="info" show> No workflow could be extracted from this history. </BAlert>
    </div>
</template>
