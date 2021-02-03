<template>
    <markdown class="p-3" :markdown-config="markdownConfig" @onEdit="onEdit" />
</template>

<script>
import axios from "axios";
import { Toast } from "ui/toast";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";
import Markdown from "components/Markdown/Markdown.vue";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

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
    data() {
        return {
            markdownConfig: {},
            invocationMarkdown: null,
        };
    },
    created() {
        this.getMarkdown(this.invocationId)
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
        async getMarkdown(id) {
            const url = `${getAppRoot()}api/invocations/${id}/report`;
            try {
                const { data } = await axios.get(url);
                return data;
            } catch (e) {
                rethrowSimple(e);
            }
        },
    },
};
</script>
