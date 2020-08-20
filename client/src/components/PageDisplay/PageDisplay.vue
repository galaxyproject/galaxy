<template>
    <markdown :markdown-config="markdownConfig" :export-link="exportUrl" @onEdit="onEdit" />
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
        dataUrl() {
            return `${getAppRoot()}api/pages/${this.pageId}`;
        },
        exportUrl() {
            return `${this.dataUrl}.pdf`;
        },
        editUrl() {
            return `${getAppRoot()}page/edit_content?id=${this.pageId}`;
        },
    },
    data() {
        return {
            markdownConfig: {},
        };
    },
    created() {
        this.getContent().then((data) => {
            this.markdownConfig = { ...data, markdown: data.content };
        });
    },
    methods: {
        onEdit() {
            window.location = this.editUrl;
        },
        async getContent() {
            try {
                const response = await axios.get(this.dataUrl);
                return response.data;
            } catch (e) {
                return `Failed to retrieve content. ${e}`;
            }
        },
    },
};
</script>
