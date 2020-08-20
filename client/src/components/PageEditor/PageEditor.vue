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
        <page-editor-html
            v-if="contentFormat == 'html'"
            :page-id="pageId"
            :content="content"
            @onUpdate="onUpdate"
        />
        <page-editor-markdown
            v-if="contentFormat == 'markdown'"
            :page-id="pageId"
            :markdown-text="content"
            @onUpdate="onUpdate"
        />
    </span>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import { save } from "./util";
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
            default: "",
        },
        contentFormat: {
            type: String,
            default: "html",
        },
        title: {
            type: String,
            default: "",
        },
    },
    methods: {
        onUpdate: function (newContent) {
            this.content = newContent;
        },
        saveContent: function () {
            save(this.pageId, this.content);
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
