<template>
    <ConfigProvider v-slot="{ config, loading }">
        <Markdown
            v-if="!loading"
            :markdown-config="markdownConfig"
            :enable_beta_markdown_export="config.enable_beta_markdown_export"
            :export-link="exportUrl"
            :download-endpoint="stsUrl(config)"
            @onEdit="onEdit" />
    </ConfigProvider>
</template>

<script>
import BootstrapVue from "bootstrap-vue";
import Markdown from "components/Markdown/Markdown";
import ConfigProvider from "components/providers/ConfigProvider";
import { Toast } from "composables/toast";
import { withPrefix } from "utils/redirect";
import { urlData } from "utils/url";
import Vue from "vue";

Vue.use(BootstrapVue);

export default {
    components: {
        ConfigProvider,
        Markdown,
    },
    props: {
        invocationId: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            markdownConfig: {},
            invocationMarkdown: null,
        };
    },
    computed: {
        dataUrl() {
            return `/api/invocations/${this.invocationId}/report`;
        },
        exportUrl() {
            return `${this.dataUrl}.pdf`;
        },
    },
    created() {
        const url = this.dataUrl;
        urlData({ url })
            .then((response) => {
                this.markdownConfig = response;
                this.invocationMarkdown = response.invocation_markdown;
            })
            .catch((error) => {
                Toast.error(`Failed to load invocation markdown: ${error}`);
            });
    },
    methods: {
        onEdit() {
            window.location = withPrefix(`/pages/create?invocation_id=${this.invocationId}`);
        },
        stsUrl(config) {
            return `${this.dataUrl}/prepare_download`;
        },
    },
};
</script>
