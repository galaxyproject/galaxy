<template>
    <Editor
        v-if="editorConfig"
        :key="editorReloadKey"
        :workflow-id="editorConfig.id"
        :data-managers="editorConfig.dataManagers"
        :initial-version="editorConfig.initialVersion"
        :module-sections="editorConfig.moduleSections"
        :workflow-tags="editorConfig.tags"
        @update:confirmation="$emit('update:confirmation', $event)" />
</template>
<script>
import Editor from "components/Workflow/Editor/Index";
import Query from "utils/query-string-parsing";
import { urlData } from "utils/url";

export default {
    components: {
        Editor,
    },
    data() {
        return {
            storedWorkflowId: null,
            workflowId: null,
            version: null,
            editorConfig: null,
            editorReloadKey: 0,
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
            let reloadEditor = true;

            // this will only be the case the first time the route updates from a new workflow
            if (!this.storedWorkflowId && !this.workflowId) {
                reloadEditor = false;
            }

            this.storedWorkflowId = Query.get("id");
            this.workflowId = Query.get("workflow_id");
            this.version = Query.get("version");

            const params = {};

            if (this.workflowId) {
                params.workflow_id = this.workflowId;
            } else if (this.storedWorkflowId) {
                params.id = this.storedWorkflowId;
            }
            if (this.version) {
                params.version = this.version;
            }

            this.editorConfig = await urlData({ url: "/workflow/editor", params });

            if (reloadEditor) {
                this.editorReloadKey += 1;
            }
        },
    },
};
</script>
