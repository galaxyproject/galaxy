import { computed } from "vue";
import { useRoute } from "vue-router/composables";

import { useToolStore } from "@/stores/toolStore";

export type ActiveContext =
    | { contextType: "tool"; toolId: string; toolName?: string; toolVersion?: string }
    | { contextType: "dataset"; datasetId: string }
    | { contextType: "workflow_editor"; workflowId: string }
    | { contextType: "workflow_run"; workflowId: string }
    | { contextType: "job"; jobId: string; toolId?: string };

export function useActiveContext() {
    const route = useRoute();
    const toolStore = useToolStore();

    const activeContext = computed<ActiveContext | null>(() => {
        const path = route.path;
        const query = route.query;
        const params = route.params;

        // Tool form: root route with tool_id query param (but not upload1)
        if ((path === "/" || path === "") && query.tool_id && query.tool_id !== "upload1") {
            const toolId = String(query.tool_id);
            const toolName = toolStore.getToolNameById(toolId);
            const version = query.version ? String(query.version) : undefined;
            return {
                contextType: "tool",
                toolId,
                toolName: toolName !== "..." ? toolName : undefined,
                toolVersion: version,
            };
        }

        // Workflow run via root route
        if ((path === "/" || path === "") && query.workflow_id) {
            return {
                contextType: "workflow_run",
                workflowId: String(query.workflow_id),
            };
        }

        // Dataset view: /datasets/:datasetId
        if (path.startsWith("/datasets/") && params.datasetId) {
            return {
                contextType: "dataset",
                datasetId: String(params.datasetId),
            };
        }

        // Workflow editor: /workflows/edit?id=X
        if (path === "/workflows/edit" && query.id) {
            return {
                contextType: "workflow_editor",
                workflowId: String(query.id),
            };
        }

        // Workflow run: /workflows/run?id=X
        if (path === "/workflows/run" && query.id) {
            return {
                contextType: "workflow_run",
                workflowId: String(query.id),
            };
        }

        // Job details: /jobs/:jobId
        if (path.startsWith("/jobs/") && params.jobId) {
            return {
                contextType: "job",
                jobId: String(params.jobId),
            };
        }

        return null;
    });

    const contextLabel = computed<string | null>(() => {
        const ctx = activeContext.value;
        if (!ctx) {
            return null;
        }
        switch (ctx.contextType) {
            case "tool":
                return `Tool: ${ctx.toolName || ctx.toolId}`;
            case "dataset":
                return `Dataset: ${ctx.datasetId}`;
            case "workflow_editor":
                return `Editing workflow: ${ctx.workflowId}`;
            case "workflow_run":
                return `Running workflow: ${ctx.workflowId}`;
            case "job":
                return `Job: ${ctx.jobId}`;
            default:
                return null;
        }
    });

    return {
        activeContext,
        contextLabel,
    };
}
