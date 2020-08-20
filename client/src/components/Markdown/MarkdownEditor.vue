<template>
    <div style="display: flex; flex: 1; flex-direction: column;">
        <div class="unified-panel-header" unselectable="on">
            <div class="unified-panel-header-inner">
                <div class="panel-header-buttons">
                    <b-button
                        title="Insert Dataset"
                        variant="link"
                        role="button"
                        v-b-tooltip.hover.bottom
                        @click="selectDataset"
                    >
                        <span class="fa fa-file" />
                    </b-button>
                    <b-button
                        title="Insert Dataset Collection"
                        variant="link"
                        role="button"
                        v-b-tooltip.hover.bottom
                        @click="selectDatasetCollection"
                    >
                        <span class="fa fa-folder" />
                    </b-button>
                    <b-button
                        title="Insert Workflow Display"
                        variant="link"
                        role="button"
                        v-b-tooltip.hover.bottom
                        @click="selectWorkflow"
                    >
                        <span class="fa fa-sitemap fa-rotate-270" />
                    </b-button>
                    <b-button
                        title="Insert Dataset as Image"
                        variant="link"
                        role="button"
                        v-b-tooltip.hover.bottom
                        @click="selectDatasetForImage"
                    >
                        <span class="fa fa-image" />
                    </b-button>
                    <b-button
                        v-if="showMarkdownHelp != null"
                        title="Show Markup Help"
                        variant="link"
                        role="button"
                        v-b-tooltip.hover.bottom
                        @click="showMarkdownHelp"
                    >
                        <span class="fa fa-question" />
                    </b-button>
                    <slot name="buttons" />
                </div>
                {{ title }}
            </div>
        </div>
        <textarea
            class="markdown-textarea"
            id="workflow-report-editor"
            v-model="content"
            @input="onUpdate"
            ref="text-area"
        />
    </div>
</template>

<script>
import _ from "underscore";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

import { dialog, datasetCollectionDialog, workflowDialog } from "utils/data";

const FENCE = "```";

export default {
    props: {
        markdownText: {
            type: String,
            default: null,
        },
        title: {
            type: String,
            default: null,
        },
        showMarkdownHelp: {
            // only used if toolbar is True - waiting on a general toolbar refactor
            type: Function,
            default: null,
        },
    },
    data() {
        return {
            content: this.markdownText,
        };
    },
    watch: {
        markdownText() {
            this.content = this.markdownText;
        },
    },
    methods: {
        onUpdate: _.debounce(function (e) {
            this.$emit("onUpdate", this.content);
        }, 300),
        insertMarkdown(markdown) {
            const textArea = this.$refs["text-area"];
            textArea.focus();
            const cursorPosition = textArea.selectionStart;
            let newContent = this.content.substr(0, cursorPosition);
            newContent += `\r\n${markdown.trim()}\r\n`;
            newContent += this.content.substr(cursorPosition);
            this.$emit("onUpdate", newContent);
        },
        insertGalaxyMarkdownBlock(block) {
            this.insertMarkdown(`${FENCE}galaxy\n${block}\n${FENCE}\n`);
        },
        _selectDataset(galaxyCall) {
            dialog(
                (response) => {
                    const datasetId = response.id;
                    this.insertGalaxyMarkdownBlock(`${galaxyCall}(history_dataset_id=${datasetId})`);
                },
                {
                    multiple: false,
                    format: null,
                    library: false, // TODO: support?
                }
            );
        },
        selectDataset() {
            this._selectDataset("history_dataset_display");
        },
        selectDatasetForImage() {
            this._selectDataset("history_dataset_as_image");
        },
        selectDatasetCollection() {
            datasetCollectionDialog((response) => {
                this.insertGalaxyMarkdownBlock(
                    `history_dataset_collection_display(history_dataset_collection_id=${response.id})`
                );
            }, {});
        },
        selectWorkflow() {
            workflowDialog((response) => {
                this.insertGalaxyMarkdownBlock(`workflow_display(workflow_id=${response.id})`);
            }, {});
        },
    },
};
</script>

<style lang="scss" scoped>
.markdown-text {
    font: 16px/1.7 Menlo, Consolas, Monaco, "Andale Mono", monospace;
}
.markdown-textarea {
    border: none;
    border-right: 1px solid #ccc;
    border-left: 1px solid #ccc;
    resize: none;
    outline: none;
    background-color: #f6f6f6;
    @extend .markdown-text;
    padding: 20px;
    width: 100%;
    flex: 1;
}
</style>
