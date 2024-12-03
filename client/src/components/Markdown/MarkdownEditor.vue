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
                    <code-editor :content="content" />
                </div>
            </div>
        </div>
        <MarkdownHelpModal ref="help" :mode="mode" />
    </div>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faQuestion } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import BootstrapVue from "bootstrap-vue";
import FlexPanel from "components/Panels/FlexPanel";
import _ from "underscore";
import Vue from "vue";

import CodeEditor from "./Editor/CodeEditor";
import MarkdownHelpModal from "./MarkdownHelpModal";
import MarkdownToolBox from "./MarkdownToolBox";

Vue.use(BootstrapVue);

library.add(faQuestion);

const FENCE = "```";

export default {
    components: {
        CodeEditor,
        FlexPanel,
        FontAwesomeIcon,
        MarkdownHelpModal,
        MarkdownToolBox,
    },
    props: {
        markdownText: {
            type: String,
            default: null,
        },
        steps: {
            type: Object,
            default: null,
        },
        title: {
            type: String,
            default: null,
        },
        mode: {
            type: String,
            default: "report",
        },
    },
    data() {
        return {
            content: this.markdownText,
        };
    },
    watch: {
        markdownText() {
            const textArea = this.$refs["text-area"];
            const textCursor = textArea.selectionEnd;
            this.content = this.markdownText;
            Vue.nextTick(() => {
                textArea.selectionEnd = textCursor;
                textArea.focus();
            });
        },
    },
    methods: {
        insertMarkdown(markdown) {
            markdown = markdown.replace(")(", ", ");
            markdown = `${FENCE}galaxy\n${markdown}\n${FENCE}\n`;
            const textArea = this.$refs["text-area"];
            textArea.focus();
            const cursorPosition = textArea.selectionStart;
            let newContent = this.content.substr(0, cursorPosition);
            newContent += `\r\n${markdown.trim()}\r\n`;
            newContent += this.content.substr(cursorPosition);
            this.$emit("update", newContent);
        },
        onUpdate: _.debounce(function (e) {
            this.$emit("update", this.content);
        }, 300),
        onHelp() {
            this.$refs.help.showMarkdownHelp();
        },
    },
};
</script>
