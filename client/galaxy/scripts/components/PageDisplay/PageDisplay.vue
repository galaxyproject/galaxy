<template>
    <markdown :markdown-config="markdownConfig" :export-link="exportUrl"> </markdown>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import Markdown from "components/Markdown/Markdown.vue";

export default {
    components: {
        Markdown,
    },
    props: {
        pageId: {
            type: String,
            required: true,
        },
    },
    computed: {
        dataUrl: function () {
            return getAppRoot() + `api/pages/${this.pageId}`;
        },
        exportUrl: function () {
            return this.dataUrl + ".pdf";
        },
    },
    data() {
        return {
            markdownConfig: {},
        };
    },
    created: function () {
        this.ajaxCall();
    },
    methods: {
        ajaxCall: function () {
            axios
                .get(this.dataUrl)
                .then((response) => {
                    this.markdownConfig = { ...response.data, markdown: response.data.content };
                })
                .catch((e) => {
                    console.error(e);
                });
        },
    },
};
</script>
