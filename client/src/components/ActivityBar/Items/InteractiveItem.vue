<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { useEntryPointStore } from "@/stores/entryPointStore";

import ActivityItem from "@/components/ActivityBar/ActivityItem.vue";

const { entryPoints } = storeToRefs(useEntryPointStore());

const totalCount = computed(() => entryPoints.value.length);

export interface Props {
    id: string;
    activityBarId: string;
    title: string;
    icon: IconDefinition;
    isActive: boolean;
    to: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "click"): void;
}>();

const tooltip = computed(() =>
    totalCount.value === 1
        ? "You currently have 1 active interactive tool"
        : `You currently have ${totalCount.value} active interactive tools`
);
</script>

<template>
    <ActivityItem
        :id="id"
        :activity-bar-id="props.activityBarId"
        :icon="icon"
        :indicator="totalCount"
        :is-active="isActive"
        :title="title"
        :tooltip="tooltip"
        :to="to"
        @click="emit('click')" />
</template>
