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
import axios from "axios";
import { Toast } from "ui/toast";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";
import ConfigProvider from "components/providers/ConfigProvider";
import Markdown from "components/Markdown/Markdown.vue";
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
            return `${getAppRoot()}api/invocations/${this.invocationId}/report`;
        },
        exportUrl() {
            return `${this.dataUrl}.pdf`;
        },
    },
    created() {
        this.getMarkdown()
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
            window.location = `${getAppRoot()}pages/create?invocation_id=${this.invocationId}`;
        },
        /** Markdown data request helper **/
        async getMarkdown() {
            try {
                const { data } = await axios.get(this.dataUrl);
                return data;
            } catch (e) {
                rethrowSimple(e);
            }
        },
    },
};
</script>
