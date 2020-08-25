<template>
    <div v-if="!edit" class="p-3">
        <markdown :markdown-config="markdownConfig" @onEdit="onEdit" />
    </div>
    <markdown-editor
        v-else
        :markdown-text="markdownConfig.invocation_markdown"
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
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
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
            this.edit = false;
            this.loadMarkdownConfig();
        },
        onUpdate(newMarkdown) {
            this.invocationMarkdown = newMarkdown;
        },
        loadMarkdownConfig() {
            const invocationId = this.invocationId;
            const url = getAppRoot() + `api/invocations/${invocationId}/report`;
            const params = {};
            if (this.invocationMarkdown) {
                params.invocation_markdown = this.invocationMarkdown;
            }
            axios
                .get(url, { params: params })
                .then((response) => {
                    this.markdownConfig = response.data;
                })
                .catch((e) => {
                    console.error(e);
                });
        },
    },
};
</script>
