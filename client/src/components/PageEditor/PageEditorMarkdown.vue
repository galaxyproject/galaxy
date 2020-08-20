<template>
    <div class="unified-panel-body editor-body">
        <markdown-editor
            :markdown-text="markdownText"
            :toolbar="true"
            :show-markdown-help="showMarkdownHelp"
            @onUpdate="onUpdate"
        />
    </div>
</template>

<script>
import MarkdownEditor from "components/Markdown/MarkdownEditor";
import { showMarkdownHelp } from "./markdownHelp";

export default {
    components: {
        MarkdownEditor,
    },
    data: function () {
        return {
            showMarkdownHelp: showMarkdownHelp,
        };
    },
    props: {
        pageId: {
            required: true,
            type: String,
        },
        markdownText: {
            type: String,
            default: "",
        },
    },
    methods: {
        onUpdate(newContent) {
            this.$emit('onUpdate', newContent);
        },
    },
};
</script>

<style scoped>
.editor-body {
    display: flex;
}
</style>