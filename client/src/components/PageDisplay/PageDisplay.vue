<template>
    <config-provider v-slot="{ config, loading }">
        <Published :item="page">
            <template v-slot>
                <div v-if="!loading">
                    <markdown
                        v-if="page.content_format == 'markdown'"
                        :markdown-config="page"
                        :enable_beta_markdown_export="config.enable_beta_markdown_export"
                        :download-endpoint="stsUrl(config)"
                        :export-link="exportUrl"
                        @onEdit="onEdit" />
                    <PageHtml v-else :page="page" />
                </div>
                <b-alert v-else variant="info" show>Unsupported page format.</b-alert>
            </template>
        </Published>
    </config-provider>
</template>

<script>
import { urlData } from "utils/url";
import { withPrefix } from "utils/redirect";
import ConfigProvider from "components/providers/ConfigProvider";
import Markdown from "components/Markdown/Markdown";
import Published from "components/Common/Published";
import PageHtml from "./PageHtml";

export default {
    components: {
        ConfigProvider,
        Markdown,
        PageHtml,
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
            return `/pages/editor?id=${this.pageId}`;
        },
    },
    created() {
        urlData({ url: this.dataUrl }).then((data) => {
            this.page = data;
        });
    },
    methods: {
        onEdit() {
            window.location = withPrefix(this.editUrl);
        },
        stsUrl(config) {
            return `${this.dataUrl}/prepare_download`;
        },
    },
};
</script>
