<template>
    <config-provider v-slot="{ config, loading }">
        <Published :details="markdownConfig">
            <template v-slot>
                <markdown
                    v-if="!loading"
                    :markdown-config="markdownConfig"
                    :enable_beta_markdown_export="config.enable_beta_markdown_export"
                    :download-endpoint="stsUrl(config)"
                    :export-link="exportUrl"
                    @onEdit="onEdit" />
            </template>
        </Published>
    </config-provider>
</template>

<script>
import { safePath } from "utils/redirect";
import { urlData } from "utils/url";
import ConfigProvider from "components/providers/ConfigProvider";
import Markdown from "components/Markdown/Markdown";
import Published from "components/Common/Published"
export default {
    components: {
        ConfigProvider,
        Markdown,
        Published,
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
