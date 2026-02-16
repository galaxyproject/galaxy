<script setup lang="ts">
import { computed } from "vue";

import { useHistoryStore } from "@/stores/historyStore";

import MarkdownEditor from "@/components/Markdown/MarkdownEditor.vue";

const props = defineProps<{
    historyId: string;
    content: string;
}>();

const emit = defineEmits<{
    (e: "update:content", content: string): void;
}>();

const historyStore = useHistoryStore();

const editorTitle = computed(() => {
    const history = historyStore.getHistoryById(props.historyId);
    return history?.name || "History Notebook";
});

function handleUpdate(newContent: string) {
    emit("update:content", newContent);
}
</script>

<template>
    <div class="history-notebook-editor" data-description="history notebook editor">
        <MarkdownEditor :markdown-text="content" mode="history_notebook" :title="editorTitle" @update="handleUpdate" />
    </div>
</template>

<style scoped>
.history-notebook-editor {
    height: 100%;
}
</style>
