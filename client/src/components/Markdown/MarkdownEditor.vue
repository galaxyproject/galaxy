<template>
    <div id="columns">
        <div id="center" class="d-flex flex-column h-100 w-100">
            <div class="unified-panel-header" unselectable="on">
                <div class="unified-panel-header-inner">
                    <div class="my-1">
                        {{ title }}
                    </div>
                    <div>
                        <b-form-radio-group
                            v-model="editor"
                            v-b-tooltip.hover.bottom
                            button-variant="outline-primary"
                            buttons
                            size="sm"
                            title="Editor"
                            :options="editorOptions" />
                        <slot name="buttons" />
                        <b-button v-b-tooltip.hover.bottom title="Help" variant="link" role="button" @click="onHelp">
                            <FontAwesomeIcon icon="question" />
                        </b-button>
                    </div>
                </div>
            </div>
            <div class="unified-panel-body">
                <TextEditor
                    v-if="editor === 'text'"
                    :title="title"
                    :markdown-text="markdownText"
                    :steps="steps"
                    :mode="mode"
                    @update="$emit('update', $event)" />
                <CellEditor
                    v-else
                    :title="title"
                    :markdown-text="markdownText"
                    :steps="steps"
                    :mode="mode"
                    @update="$emit('update', $event)" />
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
import { ref } from "vue";

import CellEditor from "./Editor/CellEditor.vue";
import TextEditor from "./Editor/TextEditor.vue";
import MarkdownHelp from "@/components/Markdown/MarkdownHelp.vue";

library.add(faQuestion);

defineProps<{
    markdownText: string;
    steps: Record<string, any>;
    title: string;
    mode: "report" | "page";
}>();

const showHelpModal = ref<boolean>(false);

const editorOptions = ref([
    { text: "Text", value: "text" },
    { text: "Cells", value: "cells" },
]);

const editor = ref("text");

function onHelp() {
    showHelpModal.value = true;
}
</script>
