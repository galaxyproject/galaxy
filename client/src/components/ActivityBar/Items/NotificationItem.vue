<script setup lang="ts">
import { type IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { useNotificationsStore } from "@/stores/notificationsStore";

import ActivityItem from "@/components/ActivityBar/ActivityItem.vue";

const { totalUnreadCount } = storeToRefs(useNotificationsStore());

export interface Props {
    id: string;
    activityBarId: string;
    title: string;
    icon: IconDefinition;
    isActive: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "click"): void;
}>();

const tooltip = computed(() =>
    totalUnreadCount.value > 0
        ? `您有 ${totalUnreadCount.value} 条未读信息`
        : "您无未读信息"
);
</script>

<template>
    <ActivityItem
        :id="id"
        :activity-bar-id="props.activityBarId"
        :icon="icon"
        :indicator="totalUnreadCount"
        :is-active="isActive"
        :title="title"
        :tooltip="tooltip"
        @click="emit('click')" />
</template>
