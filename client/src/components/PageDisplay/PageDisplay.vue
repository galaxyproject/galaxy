<template>
    <PublishedItem :item="page">
        <template v-slot>
            <div v-if="isConfigLoaded">
                <Markdown
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
    </PublishedItem>
</template>

<script>
import { useConfig } from "@/composables/config";
import { withPrefix } from "@/utils/redirect";
import { urlData } from "@/utils/url";

import PageHtml from "./PageHtml.vue";
import PublishedItem from "@/components/Common/PublishedItem.vue";
import Markdown from "@/components/Markdown/Markdown.vue";

export default {
    components: {
        Markdown,
        PageHtml,
        PublishedItem,
    },
    props: {
        pageId: {
            type: String,
            required: true,
        },
    },
    setup() {
        const { config, isConfigLoaded } = useConfig(true);
        return { config, isConfigLoaded };
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
