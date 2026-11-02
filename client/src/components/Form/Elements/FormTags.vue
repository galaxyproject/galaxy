<script setup lang="ts">
import { computed } from "vue";

import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";

defineOptions({
    // Under @vue/compat, keep v-model on modelValue instead of Vue 2's value/input
    compatConfig: { COMPONENT_V_MODEL: false },
});

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
