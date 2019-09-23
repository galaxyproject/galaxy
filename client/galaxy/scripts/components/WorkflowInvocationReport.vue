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
        invocationId: {
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
        const invocationId = this.invocationId;
        const url = getAppRoot() + `api/invocations/${invocationId}/report`;
        this.ajaxCall(url);
    },
    methods: {
        ajaxCall: function(url) {
            axios
                .get(url)
                .then(response => {
                    this.markdownConfig = response.data;
                })
                .catch(e => {
                    console.error(e);
                });
        }
    }
};
</script>
