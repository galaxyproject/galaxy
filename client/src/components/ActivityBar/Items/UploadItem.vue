<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { storeToRefs } from "pinia";
import { onMounted } from "vue";

import { useActivityStore } from "@/stores/activityStore";
import { useUploadStore } from "@/stores/uploadStore";
import Query from "@/utils/query-string-parsing.js";

import ActivityItem from "@/components/ActivityBar/ActivityItem.vue";

export interface Props {
    id: string;
    activityBarId: string;
    title: string;
    icon: IconDefinition;
    tooltip: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "click"): void;
}>();

const activityStore = useActivityStore(props.activityBarId);
const { percentage, status } = storeToRefs(useUploadStore());
const { toggledSideBar } = storeToRefs(activityStore);

function openUploadPanel() {
    activityStore.ensureVisible("upload");
    activityStore.toggleSideBar("upload");
}

onMounted(() => {
    if (Query.get("tool_id") == "upload1") {
        activityStore.ensureVisible("upload");
        activityStore.ensureSideBarOpen("upload");
    }
});

function onUploadModal() {
    emit("click");
    openUploadPanel();
}
</script>

<template>
    <ActivityItem
        :id="id"
        :activity-bar-id="props.activityBarId"
        :title="title"
        :tooltip="tooltip"
        :icon="icon"
        :is-active="toggledSideBar === 'upload'"
        :progress-percentage="percentage"
        :progress-status="status"
        @click="onUploadModal" />
</template>
