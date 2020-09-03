<template>
    <page-editor-markdown
        v-if="contentFormat == 'markdown'"
        :title="title"
        :page-id="pageId"
        :public-url="publicUrl"
        :content="content"
        :content-data="contentData"
    />
    <page-editor-html v-else :title="title" :page-id="pageId" :public-url="publicUrl" :content="content" />
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
        contentData: {
            type: Object,
            default: null,
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
