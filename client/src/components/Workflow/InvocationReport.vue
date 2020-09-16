<template>
    <div id="columns">
        <div v-show="!edit" id="center">
            <div class="h-100 overflow-auto p-3">
                <markdown :markdown-config="markdownConfig" @onEdit="onEdit" />
            </div>
        </div>
        <markdown-editor
            v-if="edit"
            :markdown-text="invocationMarkdown"
            :markdown-config="markdownConfig"
            @onUpdate="onUpdate"
        >
            <template v-slot:buttons>
                <b-button
                    id="workflow-canvas-button"
                    title="View Report"
                    variant="link"
                    role="button"
                    v-b-tooltip.hover.bottom
                    @click="onView"
                >
                    <font-awesome-icon icon="eye" />
                </b-button>
            </template>
        </markdown-editor>
    </div>
</template>

<script>
import axios from "axios";
import { Toast } from "ui/toast";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";
import Markdown from "components/Markdown/Markdown.vue";
import MarkdownEditor from "components/Markdown/MarkdownEditor.vue";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEye } from "@fortawesome/free-solid-svg-icons";

Vue.use(BootstrapVue);

library.add(faEye);

export default {
    components: {
        Markdown,
        MarkdownEditor,
        FontAwesomeIcon,
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
            edit: false,
        };
    },
    created() {
        this.loadMarkdownConfig();
    },
    methods: {
        onEdit() {
            this.edit = true;
        },
        onView() {
            this.loadMarkdownConfig().then(() => {
                this.edit = false;
            });
        },
        onUpdate(newMarkdown) {
            this.invocationMarkdown = newMarkdown;
        },
        async loadMarkdownConfig() {
            return this.getMarkdown(this.invocationId)
                .then((response) => {
                    this.markdownConfig = response;
                    this.invocationMarkdown = this.markdownConfig.invocation_markdown;
                })
                .catch((error) => {
                    Toast.error(`Failed to load invocation markdown: ${error}`);
                });
        },
        /** Markdown data request helper **/
        async getMarkdown(id) {
            const url = getAppRoot() + `api/invocations/${id}/report`;
            const params = {};
            if (this.invocationMarkdown) {
                params.invocation_markdown = this.invocationMarkdown;
            }
            try {
                const { data } = await axios.get(url, { params: params });
                return data;
            } catch (e) {
                rethrowSimple(e);
            }
        },
    },
};
</script>
