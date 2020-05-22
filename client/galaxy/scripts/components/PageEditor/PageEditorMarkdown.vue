<template>
    <div class="unified-panel-body editor-body">
        <markdown-editor
            :initial-markdown="initialContent"
            :onupdate="onUpdate"
            ref="markdownEditor"
            :toolbar="true"
            :show-markdown-help="showMarkdownHelp"
        >
        </markdown-editor>
    </div>
</template>

<script>
import MarkdownEditor from "components/Markdown/MarkdownEditor";
import { showMarkdownHelp } from "./markdownHelp";
import { save } from "./util";

export default {
    components: {
        MarkdownEditor,
    },
    data: function () {
        return {
            content: "",
            showMarkdownHelp: showMarkdownHelp,
        };
    },
    props: {
        pageId: {
            required: true,
            type: String,
        },
        initialContent: {
            type: String,
        },
    },
    methods: {
        onUpdate: function (content) {
            this.content = content;
        },
        saveContent: function () {
            save(this.pageId, this.content);
        },
    },
};
</script>

<style scoped>
.editor-body {
    display: flex;
}
</style>
