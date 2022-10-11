<template>
    <config-provider v-slot="{ config, loading }">
        <markdown
            v-if="!loading"
            :markdown-config="page"
            :enable_beta_markdown_export="config.enable_beta_markdown_export"
            :download-endpoint="stsUrl(config)"
            :export-link="exportUrl"
            @onEdit="onEdit" />
    </config-provider>
</template>

<script>
import { safePath } from "utils/redirect";
import { urlData } from "utils/url";
import ConfigProvider from "components/providers/ConfigProvider";
import Markdown from "components/Markdown/Markdown.vue";

export default {
    components: {
        ConfigProvider,
        Markdown,
    },
    props: {
        pageId: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            page: {},
        };
    },
    computed: {
        dataUrl() {
            return `/api/pages/${this.pageId}`;
        },
        exportUrl() {
            return `${this.dataUrl}.pdf`;
        },
        editUrl() {
            return `/page/edit_content?id=${this.pageId}`;
        },
    },
    created() {
        urlData({ url: this.dataUrl }).then((data) => {
            this.page = { ...data };
        });
    },
    methods: {
        onEdit() {
            window.location = safePath(this.editUrl);
        },
        stsUrl(config) {
            return `${this.dataUrl}/prepare_download`;
        },
    },
};
</script>
