<script setup lang="ts">
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";

interface Props {
    value?: string[];
    placeholder?: string;
}

const props = withDefaults(defineProps<Props>(), {
    value: () => [],
    placeholder: "Add tags",
});

const emit = defineEmits<{
    (e: "input", value: string[]): void;
}>();

function onInput(tags: string[]) {
    emit("input", tags);
}
</script>

<template>
    <StatelessTags :value="value" :placeholder="props.placeholder" @input="onInput" />
</template>
