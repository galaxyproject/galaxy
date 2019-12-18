<template>
    <markdown :markdown-config="markdownConfig"> </markdown>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import Markdown from "components/Markdown/Markdown.vue";

export default {
    components: {
        Markdown
    },
    props: {
        pageId: {
            type: String,
            required: true
        }
    },
    data() {
        return {
            markdownConfig: {}
        };
    },
    created: function() {
        const pageId = this.pageId;
        const url = getAppRoot() + `api/pages/${pageId}`;
        this.ajaxCall(url);
    },
    methods: {
        ajaxCall: function(url) {
            axios
                .get(url)
                .then(response => {
                    this.markdownConfig = { ...response.data, markdown: response.data.content };
                })
                .catch(e => {
                    console.error(e);
                });
        }
    }
};
</script>
