<template>
    <Markdown
        v-if="isConfigLoaded"
        :markdown-config="markdownConfig"
        :enable_beta_markdown_export="config.enable_beta_markdown_export"
        :export-link="exportUrl"
        :download-endpoint="stsUrl(config)"
        @onEdit="onEdit" />
</template>

<script>
import BootstrapVue from "bootstrap-vue";
import Markdown from "components/Markdown/Markdown";
import { Toast } from "composables/toast";
import { withPrefix } from "utils/redirect";
import { urlData } from "utils/url";
import Vue from "vue";

import { useConfig } from "@/composables/config";

Vue.use(BootstrapVue);

export default {
    components: {
        Markdown,
    },
    props: {
        invocationId: {
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
                Toast.error(`未能加载调用过程markdown: ${error}`);
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
