<template>
    <Editor
        v-if="storedWorkflowId || newWorkflow"
        :key="editorReloadKey"
        :workflow-id="storedWorkflowId"
        :initial-version="version"
        :subworkflow-trail="subworkflowTrail"
        :upgrade-step-order-index="upgradeStepOrderIndex"
        @update:confirmation="$emit('update:confirmation', $event)"
        @skipNextReload="() => (skipNextReload = true)" />
</template>
<script>
import { getWorkflowInfo } from "@/api/workflows";
import { parseSubworkflowTrail } from "@/components/Workflow/Editor/modules/subworkflowTrail";
import Query from "@/utils/query-string-parsing";

import Editor from "@/components/Workflow/Editor/Index.vue";

function parseOrderIndex(value) {
    if (value === undefined || value === null || value === "") {
        return undefined;
    }
    const orderIndex = parseInt(value, 10);
    return Number.isNaN(orderIndex) ? undefined : orderIndex;
}

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
            subworkflowTrail: [],
            upgradeStepOrderIndex: undefined,
        };
    },
    watch: {
        "$route.query": {
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

            const versionParam = Query.get("version");
            this.version = versionParam !== undefined ? parseInt(versionParam, 10) : undefined;
            // Set when drilling into or coming back out of a subworkflow. These names must not
            // end in an existing parameter name, Query.get matches unanchored substrings.
            this.subworkflowTrail = parseSubworkflowTrail(Query.get("from_trail"));
            this.upgradeStepOrderIndex = parseOrderIndex(Query.get("upgrade_step"));
            this.storedWorkflowId = Query.get("id");
            this.workflowId = Query.get("workflow_id");
            const workflowId = this.workflowId || this.storedWorkflowId;
            if (!workflowId) {
                this.newWorkflow = true;
                if (reloadEditor) {
                    this.editorReloadKey += 1;
                }
                return;
            }
            this.newWorkflow = false;
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
