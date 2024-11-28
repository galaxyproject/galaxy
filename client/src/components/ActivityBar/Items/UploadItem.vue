<script setup lang="ts">
import { type IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { storeToRefs } from "pinia";
import { onMounted } from "vue";

import { useGlobalUploadModal } from "@/composables/globalUploadModal.js";
import { useUploadStore } from "@/stores/uploadStore";
import Query from "@/utils/query-string-parsing.js";

import ActivityItem from "@/components/ActivityBar/ActivityItem.vue";

export interface Props {
    id: string;
    title: string;
    icon: IconDefinition;
    tooltip: string;
}

defineProps<Props>();

const emit = defineEmits<{
    (e: "click"): void;
}>();

const { openGlobalUploadModal } = useGlobalUploadModal();
const { percentage, status } = storeToRefs(useUploadStore());

onMounted(() => {
    if (Query.get("tool_id") == "upload1") {
        openGlobalUploadModal();
    }
});

function onUploadModal() {
    emit("click");
    openGlobalUploadModal();
}
</script>

<template>
    <ActivityItem
        :id="id"
        :activity-bar-id="id"
        :title="title"
        :tooltip="tooltip"
        :icon="icon"
        :progress-percentage="percentage"
        :progress-status="status"
        @click="onUploadModal" />
</template>
