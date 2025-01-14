<template>
    <TextEditor :title="title" :markdown-text="markdownText" :steps="steps" :mode="mode" />
</template>

<script setup lang="ts">
import TextEditor from "./Editor/TextEditor.vue";

defineProps({
    markdownText: {
        type: String,
        default: null,
    },
    steps: {
        type: Object,
        default: null,
    },
    title: {
        type: String,
        default: null,
    },
    mode: {
        type: String,
        default: "report",
    },
});
</script>
