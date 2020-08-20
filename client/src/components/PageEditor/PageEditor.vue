<template>
    <span>
        <div class="unified-panel-header" unselectable="on">
            <div class="unified-panel-header-inner">
                <div class="panel-header-buttons">
                    <b-button
                        id="save-button"
                        title="Save"
                        variant="link"
                        role="button"
                        v-b-tooltip.hover.bottom
                        @click="saveContent(false)"
                    >
                        <span class="fa fa-save" />
                    </b-button>
                    <b-button
                        id="view-button"
                        title="Save & View"
                        variant="link"
                        role="button"
                        v-b-tooltip.hover.bottom
                        @click="saveContent(true)"
                    >
                        <span class="fa fa-eye" />
                    </b-button>
                </div>
                {{ title }}
            </div>
        </div>
        <page-editor-html v-if="contentFormat == 'html'" :page-id="pageId" :content="content" @onUpdate="onUpdate" />
        <page-editor-markdown
            v-if="contentFormat == 'markdown'"
            :page-id="pageId"
            :markdown-text="content"
            @onUpdate="onUpdate"
        />
    </span>
</template>

<script>
import { Toast } from "ui/toast";
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
        onUpdate(newContent) {
            this.content = newContent;
        },
        saveContent(showResult) {
            save(this.pageId, this.content, !showResult)
                .then(() => {
                    if (showResult) {
                        window.location = `${getAppRoot()}${this.publicUrl}`;
                    }
                })
                .catch((error) => {
                    Toast.error(`Failed to save page: ${error}`);
                });
        },
    },
    components: {
        PageEditorHtml,
        PageEditorMarkdown,
    },
};
</script>
