import { faArrowLeft, faEye, faPlay } from "@fortawesome/free-solid-svg-icons";
import { useEventBus } from "@vueuse/core";

import { GalaxyApi } from "@/api";
import { type WorkflowInvocation } from "@/api/invocations";
import { type StoredWorkflowDetailed } from "@/api/workflows";
import { useHistoryStore } from "@/stores/historyStore";
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
 * Request and return invocations for the given workflow (and current user) from server
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
    if (userStore.currentUser?.isAnonymous || !userStore.currentUser || !extraProps || !extraProps["workflow_id"]) {
        // TODO: maybe raise an error here?
        return [[], 0];
    }
    const workflowId = extraProps["workflow_id"] as string;

    const { response, data, error } = await GalaxyApi().GET("/api/invocations", {
        params: {
            query: {
                limit,
                offset,
                sort_by: sort_by as SortKeyLiteral,
                sort_desc,
                user_id: userStore.currentUser.id,
                workflow_id: workflowId,
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
 * Fetch histories for the given workflow's invocations, if not already loaded,
 * so that they are cached and names are available for display in the grid
 */
function fetchHistories(invocations: Array<WorkflowInvocation>) {
    const historyStore = useHistoryStore();
    const historyIds: Set<string> = new Set();
    invocations.forEach((invocation) => {
        historyIds.add(invocation.history_id);
    });
    historyIds.forEach(
        (history_id) => historyStore.getHistoryById(history_id) || historyStore.loadHistoryById(history_id)
    );
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
        key: "view",
        title: "View",
        type: "button",
        icon: faEye,
        handler: (data) => {
            emit(`/workflows/invocations/${(data as WorkflowInvocation).id}`);
        },
        converter: () => "",
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
    id: "invocations-workflow-grid",
    actions: actions,
    fields: fields,
    getData: getData,
    plural: "Workflow Invocations",
    sortBy: "create_time",
    sortDesc: true,
    sortKeys: ["create_time"],
    title: "Workflow Invocations For Workflow",
};

export default gridConfig;
