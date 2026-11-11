import { GalaxyApi, type GalaxyApiPaths } from "@/api";
import type { WorkflowInvocation } from "@/api/invocations";
import { useHistoryStore } from "@/stores/historyStore";
import { useWorkflowStore } from "@/stores/workflowStore";
import { rethrowSimple } from "@/utils/simple-error";

/** Query parameters of `GET /api/invocations` */
export type InvocationsQuery = NonNullable<GalaxyApiPaths["/api/invocations"]["get"]["parameters"]["query"]>;

/** Which names to load for the returned invocations; a list scoped to one history or workflow skips that one */
interface NameLookups {
    histories?: boolean;
    workflows?: boolean;
}

/**
 * Request invocations from the server and cache the names needed to display them
 */
export async function fetchInvocations(
    query: InvocationsQuery,
    { histories = true, workflows = true }: NameLookups = {},
) {
    const { response, data, error } = await GalaxyApi().GET("/api/invocations", { params: { query } });
    if (error) {
        rethrowSimple(error);
    }
    fetchHistoriesAndWorkflows(data, histories, workflows);
    const totalMatches = parseInt(response.headers.get("total_matches") ?? "0");
    return [data, totalMatches] as const;
}

/**
 * Fetch histories and workflows for the given invocations, if not already loaded,
 * so that they are cached and names are available for display in the grid
 */
function fetchHistoriesAndWorkflows(invocations: Array<WorkflowInvocation>, histories: boolean, workflows: boolean) {
    const historyStore = useHistoryStore();
    const workflowStore = useWorkflowStore();

    const historyIds: Set<string> = new Set();
    const workflowIds: Set<string> = new Set();
    invocations.forEach((invocation) => {
        historyIds.add(invocation.history_id);
        workflowIds.add(invocation.workflow_id);
    });
    // Loads on a miss, with retry backoff; failures are recorded in the store.
    if (histories) {
        historyIds.forEach((history_id) => historyStore.getHistoryById(history_id));
    }
    if (workflows) {
        workflowIds.forEach((workflow_id) =>
            workflowStore
                .fetchWorkflowForInstanceIdCached(workflow_id)
                .catch((e) => console.warn(`Failed to load workflow ${workflow_id}`, e)),
        );
    }
}
