<template>
    <LoadingSpan v-if="loading" message="Loading Page" class="m-3" />
    <PageEditorMarkdown
        v-else
        :title="title"
        :page-id="pageId"
        :public-url="publicUrl"
        :content="content"
        :content-data="contentData" />
</template>

<script>
import axios from "axios";
import LoadingSpan from "components/LoadingSpan";
import { Toast } from "composables/toast";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";

import PageEditorMarkdown from "./PageEditorMarkdown";

import ActivityBar from "@/components/ActivityBar/ActivityBar.vue";

export default {
    components: {
        PageEditorMarkdown,
        LoadingSpan,
        ActivityBar,
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
