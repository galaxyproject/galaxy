<template>
    <Editor
        v-if="storedWorkflowId || newWorkflow"
        :key="editorReloadKey"
        :workflow-id="storedWorkflowId"
        :initial-version="version"
        @update:confirmation="$emit('update:confirmation', $event)"
        @skipNextReload="() => (skipNextReload = true)" />
</template>
<script>
import { getWorkflowInfo } from "@/api/workflows";
import Query from "@/utils/query-string-parsing";

import Editor from "@/components/Workflow/Editor/Index.vue";

export default {
    components: {
        Editor,
    },
    data() {
        return {
            storedWorkflowId: null,
            workflowId: null,
            version: null,
            storedWorkflow: null,
            editorReloadKey: 0,
            skipNextReload: false,
            newWorkflow: false,
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
            if (this.skipNextReload) {
                reloadEditor = false;
                this.skipNextReload = false;
            }

            this.version = Query.get("version");
            this.storedWorkflowId = Query.get("id");
            this.workflowId = Query.get("workflow_id");
            const workflowId = this.workflowId || this.storedWorkflowId;
            if (!workflowId) {
                this.newWorkflow = true;
                return;
            }
            if (this.workflowId) {
                const { id: storedWorkflowId } = await getWorkflowInfo(workflowId, this.version, true);
                this.storedWorkflowId = storedWorkflowId;
            }

            if (reloadEditor) {
                this.editorReloadKey += 1;
            }
        },
    },
};
</script>
