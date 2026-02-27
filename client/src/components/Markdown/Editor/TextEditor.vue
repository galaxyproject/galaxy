<template>
    <div class="d-flex h-100 w-100">
        <FlexPanel side="left">
            <MarkdownToolBox :steps="steps" @insert="insertMarkdown" />
        </FlexPanel>
        <textarea
            id="workflow-report-editor"
            ref="textArea"
            v-model="content"
            aria-label="markdown text editor"
            class="markdown-textarea w-100 p-4"
            :class="dropHighlight && `page-dragover-${dropHighlight}`"
            @input="onUpdate"
            @dragenter.prevent="onDragEnter"
            @dragover.prevent="onDragOver"
            @dragleave.prevent="onDragLeave"
            @drop.prevent="onDrop" />
    </div>
</template>

<script setup lang="ts">
import { debounce } from "lodash";
import { nextTick, ref, watch } from "vue";

import { isHistoryItem } from "@/api";
import type { DirectiveMode } from "@/components/Markdown/directives";
import { useEventStore } from "@/stores/eventStore";

import MarkdownToolBox from "@/components/Markdown/MarkdownToolBox.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";

const props = defineProps<{
    markdownText: string;
    mode: DirectiveMode;
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
    },
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

// Drag-and-drop support (page mode only)
const eventStore = useEventStore();
const dropHighlight = ref<string | null>(null);
const dragTarget = ref<EventTarget | null>(null);

function getDroppableItem(): { id: string; contentType: string } | null {
    if (props.mode !== "page") {
        return null;
    }
    const items = eventStore.getDragItems();
    if (!items || items.length === 0) {
        return null;
    }
    const item = items[0];
    if (!item || !isHistoryItem(item)) {
        return null;
    }
    const id = item.id;
    const contentType = item.history_content_type;
    if (!id) {
        return null;
    }
    return { id, contentType };
}

function onDragEnter(evt: DragEvent) {
    const droppable = getDroppableItem();
    if (droppable) {
        dragTarget.value = evt.target;
        dropHighlight.value = "success";
    }
}

function onDragOver(_evt: DragEvent) {
    // preventDefault handled by .prevent modifier to indicate valid drop target.
}

function onDragLeave(evt: DragEvent) {
    if (dragTarget.value === evt.target) {
        dropHighlight.value = null;
    }
}

function onDrop(_evt: DragEvent) {
    dropHighlight.value = null;
    const droppable = getDroppableItem();
    if (!droppable) {
        return;
    }
    const { id, contentType } = droppable;
    const directive =
        contentType === "dataset_collection"
            ? `history_dataset_collection_display(history_dataset_collection_id=${id})`
            : `history_dataset_display(history_dataset_id=${id})`;
    insertMarkdown(directive);
}
</script>

<style scoped>
.markdown-textarea {
    border: none;
    resize: none;
    outline: none;
    font:
        14px/1.7 Menlo,
        Consolas,
        Monaco,
        "Andale Mono",
        monospace;
}

.markdown-textarea.page-dragover-success {
    background: rgba(40, 167, 69, 0.08);
    border: 2px dashed #28a745;
    outline: none;
}
</style>
