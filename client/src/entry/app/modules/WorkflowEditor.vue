<template>
    <Editor
        v-if="editorConfig"
        :id="workflowId"
        :data-managers="editorConfig.workflows"
        :initial-version="editorConfig.initialVersion"
        :module-sections="editorConfig.moduleSections"
        :tags="editorConfig.tags"
        :workflows="editorConfig.workflows" />
</template>
<script>
import store from "store";
import { urlData } from "utils/url";
import Query from "utils/query-string-parsing";
import Editor from "components/Workflow/Editor/Index.vue";
export default {
    components: {
        Editor,
    },
    data() {
        return {
            workflowId: Query.get("id"),
            editorConfig: null,
        };
    },
    created() {
        this.getState();
    },
    methods: {
        async getState() {
            this.editorConfig = await urlData({ url: `workflow/editor?id=${this.workflowId}` });
        },
    },
};
</script>
