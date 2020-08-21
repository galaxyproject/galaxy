<template>
    <div class="markdown-editor h-100">
        <div class="unified-panel-header" unselectable="on">
            <div class="unified-panel-header-inner">
                <div class="panel-header-buttons">
                    <MarkdownToolbar
                        :valid-arguments="markdownConfig.valid_arguments"
                        :nodes="nodes"
                        @onInsert="onInsert"
                    />
                    <slot name="buttons" />
                </div>
                <div class="my-1">
                    {{ title }}
                </div>
            </div>
        </div>
        <div class="unified-panel-body d-flex">
            <textarea
                class="markdown-textarea"
                id="workflow-report-editor"
                v-model="content"
                @input="onUpdate"
                ref="text-area"
            />
        </div>
    </div>
</template>

<script>
import _ from "underscore";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import MarkdownToolbar from "./MarkdownToolbar";

Vue.use(BootstrapVue);

const FENCE = "```";

export default {
    components: {
        MarkdownToolbar,
    },
    props: {
        markdownText: {
            type: String,
            default: null,
        },
        markdownConfig: {
            type: Object,
            default: null,
        },
        nodes: {
            type: Object,
            default: null,
        },
        title: {
            type: String,
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
        onInsert(markdown) {
            markdown = `${FENCE}galaxy\n${markdown}\n${FENCE}\n`;
            const textArea = this.$refs["text-area"];
            textArea.focus();
            const cursorPosition = textArea.selectionStart;
            let newContent = this.content.substr(0, cursorPosition);
            newContent += `\r\n${markdown.trim()}\r\n`;
            newContent += this.content.substr(cursorPosition);
            this.$emit("onUpdate", newContent);
        },
        onUpdate: _.debounce(function (e) {
            this.$emit("onUpdate", this.content);
        }, 300),
    },
};
</script>

<style lang="scss" scoped>
.markdown-editor {
    display: flex;
    flex: 1;
    flex-direction: column;
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
