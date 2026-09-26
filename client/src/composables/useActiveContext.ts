import { faFile, faMagic, faSitemap, faWrench } from "@fortawesome/free-solid-svg-icons";
import { computed } from "vue";
import { useRoute } from "vue-router/composables";

import { PAGE_LABELS } from "@/components/Page/constants";
import { useToolStore } from "@/stores/toolStore";

export type ActiveContext =
    | { contextType: "tool"; toolId: string; toolName?: string; toolVersion?: string }
    | { contextType: "dataset"; datasetId: string }
    | { contextType: "workflow_editor"; workflowId: string }
    | { contextType: "workflow_run"; workflowId: string }
    | { contextType: "job"; jobId: string; toolId?: string }
    | { contextType: "notebook"; pageId: string; historyId?: string; invocationId?: string };

export function useActiveContext() {
    const route = useRoute();
    const toolStore = useToolStore();

    const activeContext = computed<ActiveContext | null>(() => {
        const path = route.path;
        const query = route.query;
        const params = route.params;

        // upload1 is the upload modal, not a normal tool form -- skip it.
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

        if ((path === "/" || path === "") && query.workflow_id) {
            return {
                contextType: "workflow_run",
                workflowId: String(query.workflow_id),
            };
        }

        if (path.startsWith("/datasets/") && params.datasetId) {
            return {
                contextType: "dataset",
                datasetId: String(params.datasetId),
            };
        }

        if (path === "/workflows/edit" && query.id) {
            return {
                contextType: "workflow_editor",
                workflowId: String(query.id),
            };
        }

        if (path === "/workflows/run" && query.id) {
            return {
                contextType: "workflow_run",
                workflowId: String(query.id),
            };
        }

        if (path.startsWith("/jobs/") && params.jobId) {
            return {
                contextType: "job",
                jobId: String(params.jobId),
            };
        }

        if (path.startsWith("/workflows/invocations/") && params.invocationId && query.id) {
            const invocationId = String(params.invocationId);
            if (path === `/workflows/invocations/${invocationId}/reports`) {
                return {
                    contextType: "notebook",
                    pageId: String(query.id),
                    invocationId,
                };
            }
        }

        if (path.startsWith("/histories/") && params.historyId && params.pageId) {
            const historyId = String(params.historyId);
            const pageId = String(params.pageId);
            if (path === `/histories/${historyId}/pages/${pageId}`) {
                return {
                    contextType: "notebook",
                    pageId,
                    historyId,
                    invocationId: query.invocation_id ? String(query.invocation_id) : undefined,
                };
            }
        }

        if (path === "/pages/editor" && query.id) {
            return {
                contextType: "notebook",
                pageId: String(query.id),
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
            case "notebook": {
                const notebookLabels = getNotebookLabels(ctx);
                return `${notebookLabels.entityName}: ${ctx.pageId}`;
            }
            default:
                return null;
        }
    });

    const contextIcon = computed(() => {
        switch (activeContext.value?.contextType) {
            case "tool":
                return faWrench;
            case "dataset":
                return faFile;
            case "workflow_editor":
            case "workflow_run":
                return faSitemap;
            case "notebook": {
                const notebookLabels = getNotebookLabels(activeContext.value);
                return notebookLabels.titleIcon;
            }
            default:
                return faMagic;
        }
    });

    function getNotebookLabels(noteBookContext: Extract<ActiveContext, { contextType: "notebook" }>) {
        if (noteBookContext.invocationId) {
            return PAGE_LABELS.invocation;
        } else if (noteBookContext.historyId) {
            return PAGE_LABELS.history;
        } else {
            return PAGE_LABELS.standalone;
        }
    }

    return {
        activeContext,
        contextIcon,
        contextLabel,
    };
}
