import { faArrowLeft, faPlay } from "@fortawesome/free-solid-svg-icons";
import { useEventBus } from "@vueuse/core";

import { GalaxyApi } from "@/api";
import { type WorkflowInvocation } from "@/api/invocations";
import { type StoredWorkflowDetailed } from "@/api/workflows";
import { useUserStore } from "@/stores/userStore";
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
 * Request and return invocations for the given history (and current user) from server
 */
async function getData(
    offset: number,
    limit: number,
    search: string,
    sort_by: string,
    sort_desc: boolean,
    extraProps?: Record<string, unknown>
) {
    const userStore = useUserStore();
    if (userStore.currentUser?.isAnonymous || !userStore.currentUser || !extraProps || !extraProps["history_id"]) {
        // TODO: maybe raise an error here?
        return [[], 0];
    }
    const historyId = extraProps["history_id"] as string;

    const { response, data, error } = await GalaxyApi().GET("/api/invocations", {
        params: {
            query: {
                limit,
                offset,
                sort_by: sort_by as SortKeyLiteral,
                sort_desc,
                user_id: userStore.currentUser.id,
                include_nested_invocations: false,
                history_id: historyId,
            },
        },
    });
    if (error) {
        rethrowSimple(error);
    }

    fetchHistories(data);
    const totalMatches = parseInt(response.headers.get("total_matches") ?? "0");
    return [data, totalMatches];
}

/**
 * Fetch workflows for the given history's invocations, if not already loaded,
 * so that they are cached and names are available for display in the grid
 */
function fetchHistories(invocations: Array<WorkflowInvocation>) {
    const workflowStore = useWorkflowStore();
    const workflowIds: Set<string> = new Set();
    invocations.forEach((invocation) => {
        workflowIds.add(invocation.workflow_id);
    });
    workflowIds.forEach((workflow_id) => workflowStore.fetchWorkflowForInstanceIdCached(workflow_id));
}

/**
 * Actions are grid-wide operations
 */
const actions: ActionArray = [
    {
        title: "Invocations List",
        icon: faArrowLeft,
        handler: () => {
            emit("/workflows/invocations");
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
    id: "invocations-history-grid",
    actions: actions,
    fields: fields,
    getData: getData,
    plural: "Workflow Invocations",
    sortBy: "create_time",
    sortDesc: true,
    sortKeys: ["create_time"],
    title: "Workflow Invocations For History",
};

export default gridConfig;
