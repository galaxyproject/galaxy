import { faEye } from "@fortawesome/free-solid-svg-icons";

import { type WorkflowInvocation } from "@/api/invocations";
import { getAppRoot } from "@/onload";

import { type FieldArray, type GridConfig } from "./types";

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
    // extra props will be Record<string, Invocation>; get array of invocations
    const data = Object.values(extraProps ?? {}) as WorkflowInvocation[];
    const totalMatches = data.length;
    return [data, totalMatches];
}

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
            const url = `${getAppRoot()}workflows/invocations/${(data as WorkflowInvocation).id}`;
            window.open(url, "_blank");
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
];

/**
 * Grid configuration
 */
const gridConfig: GridConfig = {
    id: "invocations-batch-grid",
    fields: fields,
    getData: getData,
    plural: "Workflow Invocations",
    sortBy: "create_time",
    sortDesc: true,
    sortKeys: [],
    title: "Workflow Invocations in Batch",
};

export default gridConfig;
