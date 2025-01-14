<template>
    <div id="columns" class="d-flex">
        <FlexPanel side="left">
            <MarkdownToolBox :steps="steps" @insert="insertMarkdown" />
        </FlexPanel>
        <div id="center" class="overflow-auto w-100">
            <div class="markdown-editor h-100">
                <div class="unified-panel-header" unselectable="on">
                    <div class="unified-panel-header-inner">
                        <div class="panel-header-buttons">
                            <slot name="buttons" />
                            <b-button
                                v-b-tooltip.hover.bottom
                                title="Help"
                                variant="link"
                                role="button"
                                @click="onHelp">
                                <FontAwesomeIcon icon="question" />
                            </b-button>
                        </div>
                        <div class="my-1">
                            {{ title }}
                        </div>
                    </div>
                </div>
                <div class="unified-panel-body d-flex">
                    <textarea
                        id="workflow-report-editor"
                        ref="textArea"
                        v-model="content"
                        class="markdown-textarea"
                        @input="onUpdate" />
                </div>
            </div>
        </div>
        <b-modal v-model="showHelpModal" hide-footer>
            <template v-slot:modal-title>
                <h2 v-if="mode === 'page'" class="mb-0">Markdown Help for Pages</h2>
                <h2 v-else class="mb-0">Markdown Help for Invocation Reports</h2>
            </template>
            <MarkdownHelp :mode="mode" />
        </b-modal>
    </div>
</template>

<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faQuestion } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { debounce } from "lodash";
import { defineEmits, defineProps, nextTick, ref, watch } from "vue";

import MarkdownHelp from "@/components/Markdown/MarkdownHelp.vue";
import MarkdownToolBox from "@/components/Markdown/MarkdownToolBox.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";

library.add(faQuestion);

const props = defineProps<{
    markdownText: string;
    mode: "report" | "page";
    steps: Record<string, any>;
    title: string;
}>();

const emit = defineEmits<{
    (e: "update", value: string): void;
}>();

const content = ref<string>(props.markdownText);
const showHelpModal = ref<boolean>(false);
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

function onHelp() {
    showHelpModal.value = true;
}
</script>
