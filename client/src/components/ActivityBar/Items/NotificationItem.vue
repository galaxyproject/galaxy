<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { useNotificationsStore } from "@/stores/notificationsStore";
import ActivityItem from "components/ActivityBar/ActivityItem.vue";

const { totalUnreadCount } = storeToRefs(useNotificationsStore());

export interface Props {
    id: string;
    title: string;
    icon: string;
    isActive: boolean;
    to: string;
}

defineProps<Props>();

const emit = defineEmits<{
    (e: "click"): void;
}>();

const tooltip = computed(() =>
    totalUnreadCount.value > 0
        ? `You have ${totalUnreadCount.value} unread notifications`
        : "You have no unread notifications"
);
</script>

<template>
    <ActivityItem
        :id="id"
        :icon="icon"
        :indicator="totalUnreadCount"
        :is-active="isActive"
        :title="title"
        :tooltip="tooltip"
        :to="to"
        @click="emit('click')" />
</template>
