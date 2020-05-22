<template>
    <markdown :markdown-config="markdownConfig" v-if="!edit"></markdown>
    <markdown-editor
        :initial-markdown="markdownConfig.invocation_markdown"
        :onupdate="onupdate"
        v-else
    ></markdown-editor>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import Markdown from "components/Markdown/Markdown.vue";
import MarkdownEditor from "components/Markdown/MarkdownEditor.vue";

export default {
    components: {
        Markdown,
        MarkdownEditor,
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
    created: function () {
        this.loadMarkdownConfig();
        window.addEventListener("keyup", this.keyListener);
    },
    destroyed: function () {
        window.removeEventListener("keyup", this.keyListener);
    },
    methods: {
        keyListener: function (event) {
            const which = event.which || event.keyCode;
            // ctrl + e
            if (event.ctrlKey && which == 69) {
                if (this.edit) {
                    this.viewReport();
                } else {
                    this.editReport();
                }
            }
        },
        viewReport: function () {
            this.edit = false;
            this.loadMarkdownConfig();
        },
        editReport: function () {
            this.edit = true;
        },
        onupdate: function (newMarkdown) {
            this.invocationMarkdown = newMarkdown;
        },
        loadMarkdownConfig: function () {
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
