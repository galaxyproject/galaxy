<template>
    <config-provider v-slot="{ config, loading }">
        <markdown
            v-if="!loading"
            :markdown-config="markdownConfig"
            :enable_beta_markdown_export="config.enable_beta_markdown_export"
            :download-endpoint="stsUrl(config)"
            :export-link="exportUrl"
            @onEdit="onEdit" />
    </config-provider>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
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
            markdownConfig: {},
        };
    },
    computed: {
        dataUrl() {
            return `${getAppRoot()}api/pages/${this.pageId}`;
        },
        exportUrl() {
            return `${this.dataUrl}.pdf`;
        },
        editUrl() {
            return `${getAppRoot()}page/edit_content?id=${this.pageId}`;
        },
    },
    created() {
        this.getContent().then((data) => {
            this.markdownConfig = { ...data, markdown: data.content };
        });
    },
    methods: {
        onEdit() {
            window.location = this.editUrl;
        },
        stsUrl(config) {
            return `${this.dataUrl}/prepare_download`;
        },
        async getContent() {
            try {
                const response = await axios.get(this.dataUrl);
                return response.data;
            } catch (e) {
                return `Failed to retrieve content. ${e}`;
            }
        },
    },
};
</script>
