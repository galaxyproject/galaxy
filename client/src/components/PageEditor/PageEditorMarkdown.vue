<template>
    <markdown-editor :title="title" :markdown-text="markdownText" :markdown-config="contentData" @onUpdate="onUpdate">
        <template v-slot:buttons>
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
        </template>
    </markdown-editor>
</template>

<script>
import MarkdownEditor from "components/Markdown/MarkdownEditor";
import { Toast } from "ui/toast";
import { getAppRoot } from "onload/loadConfig";
import { save } from "./util";

export default {
    components: {
        MarkdownEditor,
    },
    data: function () {
        return {
            markdownText: this.content,
        };
    },
    props: {
        pageId: {
            required: true,
            type: String,
        },
        publicUrl: {
            required: true,
            type: String,
        },
        title: {
            type: String,
            default: null,
        },
        content: {
            type: String,
            default: null,
        },
        contentData: {
            type: Object,
            default: null,
        },
    },
    methods: {
        onUpdate(newContent) {
            this.markdownText = newContent;
        },
        saveContent(showResult) {
            save(this.pageId, this.markdownText, !showResult)
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
};
</script>
