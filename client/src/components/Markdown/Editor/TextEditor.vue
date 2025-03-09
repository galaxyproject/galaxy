<template>
    <div class="d-flex h-100 w-100">
        <FlexPanel side="left">
            <MarkdownToolBox :steps="steps" @insert="insertMarkdown" />
        </FlexPanel>
        <textarea
            id="workflow-report-editor"
            ref="textArea"
            v-model="content"
            class="markdown-textarea w-100 p-4"
            @input="onUpdate" />
    </div>
</template>

<script setup lang="ts">
import { debounce } from "lodash";
import { defineEmits, defineProps, nextTick, ref, watch } from "vue";

import MarkdownToolBox from "@/components/Markdown/MarkdownToolBox.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";

const props = defineProps<{
    markdownText: string;
    mode: "report" | "page";
    steps?: Record<string, any>;
    title: string;
}>();

const emit = defineEmits<{
    (e: "update", value: string): void;
}>();

const content = ref<string>(props.markdownText);
const textArea = ref<HTMLTextAreaElement | null>(null);

const FENCE = "```";

watch(
    () => props.markdownText,
    (newValue) => {
        const textCursor = textArea.value?.selectionEnd || 0;
        content.value = newValue;
        nextTick(() => {
            if (textArea.value) {
                textArea.value.selectionEnd = textCursor;
                textArea.value.focus();
            }
        });
    }
);

function insertMarkdown(markdown: string) {
    markdown = markdown.replace(")(", ", ");
    markdown = `${FENCE}galaxy\n${markdown}\n${FENCE}\n`;
    if (textArea.value) {
        textArea.value.focus();
        const cursorPosition = textArea.value.selectionStart;
        const newContent =
            content.value?.substr(0, cursorPosition) +
            `\r\n${markdown.trim()}\r\n` +
            content.value?.substr(cursorPosition);

        emit("update", newContent || "");
    }
}

const onUpdate = debounce((e: Event) => {
    emit("update", content.value || "");
}, 300);
</script>

<style scoped>
.markdown-textarea {
    border: none;
    resize: none;
    outline: none;
    font: 14px/1.7 Menlo, Consolas, Monaco, "Andale Mono", monospace;
}
</style>
