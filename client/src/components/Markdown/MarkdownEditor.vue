<template>
    <div style="display: flex; flex: 1; flex-direction: column;">
        <ul class="galaxymark-toolbar" ref="menu" v-if="toolbar">
            <li>
                <a
                    href="#"
                    class="fa-2x fa fa-file"
                    @click="selectDataset"
                    v-b-tooltip.hover
                    title="Insert Dataset"
                ></a>
            </li>
            <li>
                <a
                    href="#"
                    class="fa-2x fa fa-folder"
                    @click="selectDatasetCollection"
                    v-b-tooltip.hover
                    title="Insert Dataset Collection"
                ></a>
            </li>
            <li>
                <a
                    href="#"
                    class="fa-2x fa fa-sitemap fa-rotate-270"
                    @click="selectWorkflow"
                    v-b-tooltip.hover
                    title="Inseert Workflow Preview"
                ></a>
            </li>
            <li>
                <a
                    href="#"
                    class="fa-2x fa fa-image"
                    @click="selectDatasetForImage"
                    v-b-tooltip.hover
                    title="Insert Dataset as an Image"
                ></a>
            </li>
            <li>
                <a
                    href="#"
                    class="fa-2x fa fa-question"
                    @click="showMarkdownHelp"
                    v-if="showMarkdownHelp != null"
                    v-b-tooltip.hover
                    title="Show Galaxy Markdown Help"
                ></a>
            </li>
        </ul>
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
        toolbar: {
            type: Boolean,
            default: false,
        },
        showMarkdownHelp: {
            // only used if toolbar is True - waiting on a general toolbar refactor
            type: Function,
            default: null,
        }
    },
    data() {
        return {
            content: this.markdownText,
        }
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
            const cursorPosition = textArea.selectionStart;
            let newContent = this.content.substr(0, cursorPosition);
            newContent += markdown;
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
.galaxymark-toolbar {
    background: #fff;
    border-bottom: 1px solid rgba(0, 0, 0, 0.1);
    display: block;
    width: 100%;
    margin-top: 0;
    margin-bottom: 0;
    padding-left: 0;
    padding-right: 0;
}

.galaxymark-toolbar li {
    display: inline-block;
    position: relative;
    z-index: 1;
}

.galaxymark-toolbar li a {
    color: #888;
    cursor: pointer;
    display: block;
    font-size: 16px;
    height: 40px;
    line-height: 40px;
    text-align: center;
    transition: color 0.2s linear;
    width: 40px;
}

.galaxymark-toolbar li a:hover {
    color: #000;
    text-decoration: none;
}

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
