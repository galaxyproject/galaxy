<script setup lang="ts">
import { storeToRefs } from "pinia";
import { useNotificationsStore } from "@/stores/notificationsStore";
import ActivityItem from "components/ActivityBar/ActivityItem.vue";

const { totalUnreadCount } = storeToRefs(useNotificationsStore());

export interface Props {
    id: string;
    title: string;
    icon: string;
    isActive: boolean;
    tooltip: string;
    to: string;
}

defineProps<Props>();

const emit = defineEmits<{
    (e: "click"): void;
}>();
</script>

<template>
    <ActivityItem
        :id="id"
        :icon="icon"
        :is-active="isActive"
        :title="title"
        :tooltip="tooltip"
        :to="to"
        @click="emit('click')" />
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.indicator {
    position: absolute;
    top: -0.2rem;
    right: -0.1rem;
    width: 0.6rem;
    height: 0.6rem;
    border-radius: 50%;
    background: $brand-danger;
}
</style>
