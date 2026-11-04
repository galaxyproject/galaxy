import { faPlus, faRedo } from "@fortawesome/free-solid-svg-icons";
import { useEventBus } from "@vueuse/core";

import { GalaxyApi } from "@/api";
import type { WorkflowInvocation } from "@/api/invocations";
import type { StoredWorkflowDetailed } from "@/api/workflows";
import { useHistoryStore } from "@/stores/historyStore";
import { useWorkflowStore } from "@/stores/workflowStore";
import Filtering, { equals, type ValidFilter } from "@/utils/filtering";
import _l from "@/utils/localization";
import { rethrowSimple } from "@/utils/simple-error";

import type { ActionArray, FieldArray, GridConfig } from "./types";

const { emit } = useEventBus<string>("grid-router-push");

/**
 * Local types
 */
type SortKeyLiteral = "create_time" | "update_time" | "None" | null | undefined;

/**
 * `workflow` takes a stored workflow id, `history` a history id; both map to the
 * `/api/invocations` query parameters of the same name. Unkeyed text lands in `text`,
 * which the API cannot search, so `getData` rejects it.
 */
const validFilters: Record<string, ValidFilter<string>> = {
    workflow: {
        placeholder: "workflow id",
        type: String,
        handler: equals("workflow_id", "workflow_id"),
        menuItem: true,
        helpInfo: "Use the filter button next to a workflow name to show only invocations of that workflow.",
    },
    history: {
        placeholder: "history id",
        type: String,
        handler: equals("history_id", "history_id"),
        menuItem: true,
        helpInfo: "Use the filter button next to a history name to show only invocations in that history.",
    },
    text: { handler: equals("text", "text"), menuItem: false },
};

export const invocationsFiltering = new Filtering(validFilters, undefined, true, "text");

export const FREE_TEXT_UNSUPPORTED =
    "Free-text search is not available for invocations, filter with workflow: or history: instead.";

/**
 * Translate the grid's filter text into `/api/invocations` query parameters
 */
export function getInvocationQueryParams(search: string): Record<string, string> {
    const queryDict = invocationsFiltering.getQueryDict(search);
    if (queryDict.text) {
        throw new Error(FREE_TEXT_UNSUPPORTED);
    }
    const params: Record<string, string> = {};
    if (queryDict.workflow_id) {
        params.workflow_id = queryDict.workflow_id;
    }
    if (queryDict.history_id) {
        params.history_id = queryDict.history_id;
    }
    return params;
}

/**
 * Request and return invocations from server
 */
export async function getData(
    offset: number,
    limit: number,
    search: string,
    sort_by: string,
    sort_desc: boolean,
    extraProps?: Record<string, unknown>,
) {
    const params = {
        limit,
        offset,
        sort_by: sort_by as SortKeyLiteral,
        sort_desc,
        include_nested_invocations: false,
        ...getInvocationQueryParams(search),
    } as Record<string, unknown>;

    if (extraProps && "include_terminal" in extraProps) {
        params["include_terminal"] = extraProps["include_terminal"];
    }
    if (extraProps && "user_id" in extraProps) {
        params["user_id"] = extraProps["user_id"];
    }

    const { response, data, error } = await GalaxyApi().GET("/api/invocations", { params: { query: params } });
    if (error) {
        rethrowSimple(error);
    }
    fetchHistoriesAndWorkflows(data);
    const headers = response.headers;
    const totalMatches = parseInt(headers.get("total_matches") ?? "0");
    return [data, totalMatches] as const;
}

/**
 * Fetch histories and workflows for the given invocations, if not already loaded,
 * so that they are cached and names are available for display in the grid
 */
function fetchHistoriesAndWorkflows(invocations: Array<WorkflowInvocation>) {
    const historyStore = useHistoryStore();
    const workflowStore = useWorkflowStore();

    const historyIds: Set<string> = new Set();
    const workflowIds: Set<string> = new Set();
    invocations.forEach((invocation) => {
        historyIds.add(invocation.history_id);
        workflowIds.add(invocation.workflow_id);
    });
    // Loads on a miss, with retry backoff; failures are recorded in the store.
    historyIds.forEach((history_id) => historyStore.getHistoryById(history_id));
    workflowIds.forEach((workflow_id) =>
        workflowStore
            .fetchWorkflowForInstanceIdCached(workflow_id)
            .catch((e) => console.warn(`Failed to load workflow ${workflow_id}`, e)),
    );
}

/**
 * Actions are grid-wide operations
 */
const actions: ActionArray = [
    {
        title: "Import Invocation",
        icon: faPlus,
        handler: () => {
            emit("/workflows/invocations/import");
        },
    },
];

/**
 * Declare columns to be displayed
 */
const fields: FieldArray = [
    {
        key: "expand",
        title: null,
        type: "expand",
    },
    {
        key: "workflow_id",
        title: "Workflow",
        type: "link",
        handler: (data) => {
            const invocation = data as WorkflowInvocation;
            emit(`/workflows/invocations/${invocation.id}`);
        },
        converter: (data) => {
            const workflowStore = useWorkflowStore();
            const invocation = data as WorkflowInvocation;
            return workflowStore.getStoredWorkflowNameByInstanceId(invocation.workflow_id);
        },
        filter: {
            key: "workflow",
            title: "Show only invocations of this workflow",
            value: (data) => {
                const invocation = data as WorkflowInvocation;
                return useWorkflowStore().getStoredWorkflowIdByInstanceId(invocation.workflow_id);
            },
        },
    },
    {
        key: "history_id",
        title: "History",
        type: "history",
        filter: {
            key: "history",
            title: "Show only invocations in this history",
            value: (data) => (data as WorkflowInvocation).history_id,
        },
    },
    {
        key: "create_time",
        title: "Invoked",
        type: "date",
    },
    {
        key: "state",
        title: "State",
        type: "helptext",
        converter: (data) => {
            const invocation = data as WorkflowInvocation;
            return `galaxy.invocations.states.${invocation.state}`;
        },
    },
    {
        key: "execute",
        title: "Rerun",
        type: "button",
        icon: faRedo,
        condition: (data) => {
            const invocation = data as WorkflowInvocation;
            const workflowStore = useWorkflowStore();
            const workflow = workflowStore.getStoredWorkflowByInstanceId(
                invocation.workflow_id,
            ) as unknown as StoredWorkflowDetailed;
            return !workflow?.deleted;
        },
        handler: (data) => {
            const invocation = data as WorkflowInvocation;
            emit(`/workflows/rerun?invocation_id=${invocation.id}`);
        },
        converter: () => "",
    },
];

/**
 * Grid configuration
 */
const gridConfig: GridConfig = {
    id: "invocations-grid",
    actions: actions,
    fields: fields,
    filtering: invocationsFiltering,
    getData: getData,
    plural: "Workflow Invocations",
    sortBy: "create_time",
    sortDesc: true,
    sortKeys: ["create_time"],
    title: "Workflow Invocations",
};

export default gridConfig;
