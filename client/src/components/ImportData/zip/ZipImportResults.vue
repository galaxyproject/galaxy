<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";

import { useHistoryStore } from "@/stores/historyStore";

import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";

const breadcrumbItems = [
    { title: "Import individual files from archive", to: "/import/zip" },
    { title: "Results", active: true },
];

interface Props {
    workflowFileCount: number;
    regularFileCount: number;
}

defineProps<Props>();

const historyStore = useHistoryStore();
const currentHistoryName = computed(() =>
    historyStore.currentHistoryId ? historyStore.getHistoryNameById(historyStore.currentHistoryId) : undefined
);
</script>

<template>
    <div class="zip-import-results">
        <BreadcrumbHeading h1 separator inline :items="breadcrumbItems" />

        <p>
            Your selected files are being imported in the background. This may take a few minutes. Once the import
            process is complete:
        </p>

        <p v-if="workflowFileCount > 0">
            <strong>{{ workflowFileCount }} new workflow{{ workflowFileCount > 1 ? "s" : "" }}</strong> will be
            available in your <RouterLink to="/workflows/list">Workflows</RouterLink> page
        </p>

        <p v-if="regularFileCount > 0">
            <strong>{{ regularFileCount }} new file{{ regularFileCount > 1 ? "s" : "" }}</strong> will be be available
            in your currently active History
            <span v-if="currentHistoryName">
                <strong>{{ currentHistoryName }} </strong>
            </span>
        </p>
    </div>
</template>
