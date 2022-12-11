<template>
    <Editor
        v-if="editorConfig"
        :id="editorConfig.id"
        :data-managers="editorConfig.dataManagers"
        :initial-version="editorConfig.initialVersion"
        :module-sections="editorConfig.moduleSections"
        :tags="editorConfig.tags"
        :workflows="editorConfig.workflows"
        @update:confirmation="$emit('update:confirmation', $event)" />
</template>
<script>
import { urlData } from "utils/url";
import Query from "utils/query-string-parsing";
import Editor from "components/Workflow/Editor/Index";
export default {
    components: {
        Editor,
    },
    data() {
        return {
            storedWorkflowId: null,
            workflowId: null,
            editorConfig: null,
        };
    },
    watch: {
        "$route.params": {
            handler() {
                this.getEditorConfig();
            },
            immediate: true,
        },
    },
    methods: {
        async getEditorConfig() {
            const storedWorkflowId = Query.get("id");
            const workflowId = Query.get("workflow_id");
            const params = {};
            if (workflowId) {
                params.workflow_id = workflowId;
            } else if (storedWorkflowId) {
                params.id = storedWorkflowId;
            }
            this.editorConfig = await urlData({ url: "/workflow/editor", params });
        },
    },
};
</script>
