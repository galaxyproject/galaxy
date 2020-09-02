<template>
    <div id="columns" class="workflow-client">
        <SidePanel id="left" side="left">
            <template v-slot:panel>
                <MarkdownToolBox :nodes="nodes" @onInsert="onInsert" />
            </template>
        </SidePanel>
        <div id="center" class="workflow-center workflow-markdown-editor">
            <div class="markdown-editor h-100">
                <div class="unified-panel-header" unselectable="on">
                    <div class="unified-panel-header-inner">
                        <div class="panel-header-buttons">
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
        </div>
    </div>
</template>

<script>
import _ from "underscore";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import MarkdownToolBox from "./MarkdownToolBox";
import SidePanel from "components/Panels/SidePanel";

Vue.use(BootstrapVue);

const FENCE = "```";

export default {
    components: {
        MarkdownToolBox,
        SidePanel,
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
