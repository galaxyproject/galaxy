<script setup lang="ts">
import { computed } from "vue";

import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";

const props = defineProps<{
    modelValue?: string;
    placeholder?: string;
}>();

const emit = defineEmits<{
    (e: "update:modelValue", value: string): void;
}>();

const valueArray = computed(() => props.modelValue?.split(",").map((v) => v.trim()) ?? []);

function onInput(tags: string[]) {
    emit("update:modelValue", tags.join(","));
}
</script>

<template>
    <StatelessTags
        :model-value="valueArray"
        :placeholder="props.placeholder"
        @update:model-value="onInput"></StatelessTags>
</template>
