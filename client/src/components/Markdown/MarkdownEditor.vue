<template>
    <div>
        <SidePanel id="left" side="left">
            <template v-slot:panel>
                <MarkdownToolBox :steps="steps" @onInsert="onInsert" />
            </template>
        </SidePanel>
        <div id="center" class="workflow-markdown-editor">
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
                                <font-awesome-icon icon="question" />
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
                        ref="text-area"
                        v-model="content"
                        class="markdown-textarea"
                        @input="onUpdate" />
                </div>
            </div>
        </div>
        <MarkdownHelp ref="help" />
    </div>
</template>

<script>
import _ from "underscore";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faQuestion } from "@fortawesome/free-solid-svg-icons";
import MarkdownToolBox from "./MarkdownToolBox";
import SidePanel from "components/Panels/SidePanel";
import MarkdownHelp from "./MarkdownHelp";

Vue.use(BootstrapVue);

library.add(faQuestion);

const FENCE = "```";

export default {
    components: {
        MarkdownToolBox,
        SidePanel,
        FontAwesomeIcon,
        MarkdownHelp,
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
        steps: {
            type: Object,
            required: true,
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
        onInsert(markdown) {
            markdown = markdown.replace(")(", ", ");
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
        onHelp() {
            this.$refs.help.showMarkdownHelp();
        },
    },
};
</script>
