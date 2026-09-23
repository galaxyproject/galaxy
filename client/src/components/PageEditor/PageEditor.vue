<template>
    <PageEditorView :page-id="pageId" :display-only="displayOnly" :hide-header="hideHeader" />
</template>

<script setup lang="ts">
import PageEditorView from "./PageEditorView.vue";

defineProps<{
    pageId: string;
    displayOnly?: boolean;
    hideHeader?: boolean;
}>();
</script>
