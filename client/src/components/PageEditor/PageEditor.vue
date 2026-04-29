<template>
    <PageEditorView :page-id="pageId" :display-only="displayOnly" />
</template>

<script setup lang="ts">
import PageEditorView from "./PageEditorView.vue";

defineProps<{
    pageId: string;
    displayOnly?: boolean;
}>();
</script>
