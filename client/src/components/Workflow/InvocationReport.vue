<template>
    <config-provider v-slot="{ config, loading }">
        <markdown
            v-if="!loading"
            :markdown-config="markdownConfig"
            :enable_beta_markdown_export="config.enable_beta_markdown_export"
            :export-link="exportUrl"
            @onEdit="onEdit" />
    </config-provider>
</template>

<script>
import { withPrefix } from "utils/redirect";
import { urlData } from "utils/url";
import { Toast } from "composables/toast";
import ConfigProvider from "components/providers/ConfigProvider";
import Markdown from "components/Markdown/Markdown";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

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
    },
};
</script>
