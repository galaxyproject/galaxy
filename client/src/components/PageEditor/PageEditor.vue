<template>
    <LoadingSpan v-if="loading" message="Loading Page" class="m-3" />
    <page-editor-markdown
        v-else-if="contentFormat == 'markdown'"
        :title="title"
        :page-id="pageId"
        :public-url="publicUrl"
        :content="content"
        :content-data="contentData" />
    <page-editor-html v-else :title="title" :page-id="pageId" :public-url="publicUrl" :content="content" />
</template>

<script>
import axios from "axios";
import { Toast } from "ui/toast";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";
import LoadingSpan from "components/LoadingSpan";
import PageEditorHtml from "./PageEditorHtml";
import PageEditorMarkdown from "./PageEditorMarkdown";

export default {
    components: {
        PageEditorHtml,
        PageEditorMarkdown,
        LoadingSpan,
    },
    props: {
        pageId: {
            required: true,
            type: String,
        },
    },
    data() {
        return {
            title: null,
            contentFormat: null,
            contentData: null,
            content: null,
            publicUrl: null,
            loading: true,
        };
    },
    created() {
        this.getPage(this.pageId)
            .then((data) => {
                this.publicUrl = `${getAppRoot()}u/${data.username}/p/${data.slug}`;
                this.content = data.content;
                this.contentFormat = data.content_format;
                this.contentData = data;
                this.title = data.title;
                this.loading = false;
            })
            .catch((error) => {
                Toast.error(`Failed to load page: ${error}`);
            });
    },
    methods: {
        /** Page data request helper **/
        async getPage(id) {
            try {
                const { data } = await axios.get(`${getAppRoot()}api/pages/${id}`);
                return data;
            } catch (e) {
                rethrowSimple(e);
            }
        },
    },
};
</script>
