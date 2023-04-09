<script setup lang="ts">
import { ref, onMounted, onUnmounted, type Ref } from "vue";
import ActivityItem from "components/ActivityBar/ActivityItem.vue";
// @ts-ignore
import Query from "utils/query-string-parsing.js";
// @ts-ignore
import { useGlobalUploadModal } from "composables/globalUploadModal.js";
// @ts-ignore
import { eventHub } from "components/plugins/eventHub.js";

const { openGlobalUploadModal } = useGlobalUploadModal();

const status: Ref<string> = ref("success");
const percentage: Ref<number> = ref(0);

onMounted(() => {
    eventHub.$on("upload:status", setStatus);
    eventHub.$on("upload:percentage", setPercentage);
    if (Query.get("tool_id") == "upload1") {
        openGlobalUploadModal();
    }
});

onUnmounted(() => {
    eventHub.$off("upload:status", setStatus);
    eventHub.$off("upload:percentage", setPercentage);
});

function setStatus(val: string): void {
    status.value = val;
}

function setPercentage(val: number): void {
    percentage.value = val;
}
</script>

<template>
    <ActivityItem
        id="activity-upload"
        title="Upload"
        tooltip="Download from URL or upload files from disk"
        icon="upload"
        :progress-percentage="percentage"
        :progress-status="status"
        @click="openGlobalUploadModal" />
</template>
