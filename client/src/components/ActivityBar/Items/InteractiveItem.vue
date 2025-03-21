<script setup lang="ts">
import { type IconDefinition } from "@fortawesome/fontawesome-svg-core";
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
        ? "您当前有一个正在使用的互动工具"
        : `您当前有 ${totalCount.value} 个正在使用的互动工具`
);
</script>

<template>
    <ActivityItem
        v-if="totalCount > 0"
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
