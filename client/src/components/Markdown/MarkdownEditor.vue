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
                            v-if="!hasLabels"
                            v-model="editor"
                            v-g-tooltip.hover.bottom
                            button-variant="outline-primary"
                            buttons
                            size="sm"
                            title="Editor"
                            :options="editorOptions" />
                        <slot name="buttons" />
                        <b-button v-g-tooltip.hover.bottom title="Help" variant="link" role="button" @click="onHelp">
                            <FontAwesomeIcon :icon="faQuestion" />
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
                <CellEditor v-else :markdown-text="markdownText" :labels="labels" @update="$emit('update', $event)" />
            </div>
        </div>
        <GModal
            :show.sync="showHelpModal"
            size="medium"
            fixed-height
            :title="mode === 'page' ? 'Markdown Help for Pages' : 'Markdown Help for Invocation Reports'">
            <MarkdownHelp :mode="mode" />
        </GModal>
    </div>
</template>

<script setup lang="ts">
import { faQuestion } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";

import type { DirectiveMode } from "./directives";
import type { WorkflowLabel } from "./Editor/types";

import GModal from "../BaseComponents/GModal.vue";
import CellEditor from "./Editor/CellEditor.vue";
import TextEditor from "./Editor/TextEditor.vue";
import MarkdownHelp from "@/components/Markdown/MarkdownHelp.vue";

const props = defineProps<{
    markdownText: string;
    mode: DirectiveMode;
    labels?: Array<WorkflowLabel>;
    steps?: Record<string, any>;
    title: string;
}>();

const showHelpModal = ref<boolean>(false);

const hasLabels = computed(() => props.labels !== undefined);

const editor = ref("text");
const editorOptions = ref([
    { text: "Editor", value: "editor" },
    { text: "Text", value: "text" },
]);

function onHelp() {
    showHelpModal.value = true;
}
</script>
