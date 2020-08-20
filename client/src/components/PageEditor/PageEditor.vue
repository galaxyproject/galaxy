<template>
    <span>
        <page-editor-html
            v-if="contentFormat == 'html'"
            :title="title"
            :page-id="pageId"
            :public-url="publicUrl"
            :content="content"
        />
        <page-editor-markdown
            v-if="contentFormat == 'markdown'"
            :title="title"
            :page-id="pageId"
            :public-url="publicUrl"
            :content="content"
        />
    </span>
</template>

<script>
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
    components: {
        PageEditorHtml,
        PageEditorMarkdown,
    },
};
</script>
