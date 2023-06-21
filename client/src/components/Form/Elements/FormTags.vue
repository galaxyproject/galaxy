<script setup lang="ts">
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
import { computed } from "vue";

const props = defineProps<{
    value?: string;
    placeholder?: string;
}>();

const emit = defineEmits<{
    (e: "input", value: string): void;
}>();

const valueArray = computed(() => props.value?.split(",").map((v) => v.trim()) ?? []);

function onInput(tags: string[]) {
    emit("input", tags.join(","));
}
</script>

<template>
    <StatelessTags :value="valueArray" :placeholder="props.placeholder" @input="onInput"></StatelessTags>
</template>
