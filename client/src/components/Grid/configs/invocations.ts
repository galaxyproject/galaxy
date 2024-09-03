import { faPlay, faPlus } from "@fortawesome/free-solid-svg-icons";
import { useEventBus } from "@vueuse/core";

import { GalaxyApi } from "@/api";
import { type WorkflowInvocation } from "@/api/invocations";
import { type StoredWorkflowDetailed } from "@/api/workflows";
import { useHistoryStore } from "@/stores/historyStore";
import { useWorkflowStore } from "@/stores/workflowStore";
import _l from "@/utils/localization";
import { rethrowSimple } from "@/utils/simple-error";

import { type ActionArray, type FieldArray, type GridConfig } from "./types";

const { emit } = useEventBus<string>("grid-router-push");

/**
 * Local types
 */
type SortKeyLiteral = "create_time" | "update_time" | "None" | null | undefined;

/**
 * Request and return invocations from server
 */
export async function getData(
    offset: number,
    limit: number,
    search: string,
    sort_by: string,
    sort_desc: boolean,
    extraProps?: Record<string, unknown>
) {
    const params = {
        limit,
        offset,
        sort_by: sort_by as SortKeyLiteral,
        sort_desc,
        include_nested_invocations: false,
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
    return [data, totalMatches];
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
    historyIds.forEach(
        (history_id) => historyStore.getHistoryById(history_id) || historyStore.loadHistoryById(history_id)
    );
    workflowIds.forEach((workflow_id) => workflowStore.fetchWorkflowForInstanceIdCached(workflow_id));
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
    },
    {
        key: "history_id",
        title: "History",
        type: "history",
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
        title: "Run",
        type: "button",
        icon: faPlay,
        condition: (data) => {
            const invocation = data as WorkflowInvocation;
            const workflowStore = useWorkflowStore();
            const workflow = workflowStore.getStoredWorkflowByInstanceId(
                invocation.workflow_id
            ) as unknown as StoredWorkflowDetailed;
            return !workflow?.deleted;
        },
        handler: (data) => {
            const invocation = data as WorkflowInvocation;
            const workflowStore = useWorkflowStore();
            emit(`/workflows/run?id=${workflowStore.getStoredWorkflowIdByInstanceId(invocation.workflow_id)}`);
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
    getData: getData,
    plural: "Workflow Invocations",
    sortBy: "create_time",
    sortDesc: true,
    sortKeys: ["create_time"],
    title: "Workflow Invocations",
};

export default gridConfig;
