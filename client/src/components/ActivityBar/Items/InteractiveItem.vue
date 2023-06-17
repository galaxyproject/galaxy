<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { useEntryPointStore } from "@/stores/entryPointStore";
import ActivityItem from "components/ActivityBar/ActivityItem.vue";

const { entryPoints } = storeToRefs(useEntryPointStore());

const totalCount = computed(() => entryPoints.value.length)

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
</script>

<template>
    <ActivityItem
        v-if="totalCount > 0"
        :id="id"
        :icon="icon"
        :is-active="isActive"
        :title="title"
        :tooltip="`There are ${totalCount} active interactive tools.`"
        :to="to"
        @click="emit('click')" />
</template>
