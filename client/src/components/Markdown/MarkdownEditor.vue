<template>
    <TextEditor
        :title="title"
        :markdown-text="markdownText"
        :steps="steps"
        :mode="mode"
        @update="$emit('update', $event)" />
</template>

<script setup lang="ts">
import TextEditor from "./Editor/TextEditor.vue";

defineProps<{
    markdownText: string;
    steps: Record<string, any>;
    title: string;
    mode: "report" | "page";
}>();
</script>
