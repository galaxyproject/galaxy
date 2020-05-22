<template>
    <span>
        <div class="unified-panel-header" unselectable="on">
            <div class="unified-panel-header-inner">
                Page Editor: {{ title }}
                <a
                    id="save-button"
                    class="btn btn-secondary fa fa-save float-right"
                    href="javascript:void(0)"
                    @click="saveContent"
                ></a>
                <a
                    id="view-button"
                    class="btn btn-secondary fa fa-eye float-right"
                    href="javascript:void(0)"
                    @click="viewContent"
                ></a>
            </div>
        </div>
        <page-editor-html :page-id="pageId" :content="content" v-if="contentFormat == 'html'" ref="contentEditor" />
        <page-editor-markdown
            :page-id="pageId"
            :initial-content="content"
            v-if="contentFormat == 'markdown'"
            ref="contentEditor"
        />
    </span>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import PageEditorHtml from "./PageEditorHtml";
import PageEditorMarkdown from "./PageEditorMarkdown";

export default {
    props: {
        pageId: {
            required: true,
            type: String,
        },
        publicUrl: {
            required: true,
            type: String,
        },
        content: {
            type: String,
        },
        contentFormat: {
            type: String,
            default: "html",
        },
        title: {
            type: String,
        },
    },
    computed: {},
    methods: {
        saveContent: function () {
            this.$refs.contentEditor.saveContent();
        },
        viewContent: function () {
            // TODO: Future iteration, contentEditor should have an entry point that can decide
            // if it has changed content.
            const r = window.confirm(
                "This will leave the current page editor, if you have unsaved changes they will be lost. Do you wish to continue?"
            );
            if (r === true) {
                window.location = `${getAppRoot()}${this.publicUrl}`;
            }
        },
    },
    components: {
        PageEditorHtml,
        PageEditorMarkdown,
    },
};
</script>
