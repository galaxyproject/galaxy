import { type components } from "@/api/schema";
import { rethrowSimple } from "@/utils/simple-error";

import { GalaxyApi } from "./client";

export type Creator = components["schemas"]["Person"] | components["schemas"]["galaxy__schema__schema__Organization"];
export type StoredWorkflowDetailed = components["schemas"]["StoredWorkflowDetailed"];

//TODO: replace with generated schema model when available
export type WorkflowSummary = {
    model_class: string;
    id: string;
    latest_workflow_id: string;
    name: string;
    create_time: string;
    update_time: string;
    published: boolean;
    importable: boolean;
    deleted: boolean;
    hidden: boolean;
    tags: string[];
    latest_workflow_uuid: string;
    creator_deleted: boolean;
    annotations: string[];
    url: string;
    owner: string;
    source_type?: string;
    source_metadata: {
        url?: string;
        trs_server?: string;
        trs_tool_id?: string;
        trs_version_id?: string;
    };
    number_of_steps?: number;
    show_in_tool_panel: boolean;
};

export type AnyWorkflow = WorkflowSummary | StoredWorkflowDetailed;

type SortBy = "create_time" | "update_time" | "name";

interface LoadWorkflowsOptions {
    sortBy: SortBy;
    sortDesc: boolean;
    limit: number;
    offset: number;
    filterText: string;
    showPublished: boolean;
    skipStepCounts: boolean;
}

export async function loadWorkflows({
    sortBy = "update_time",
    sortDesc = true,
    limit = 20,
    offset = 0,
    filterText = "",
    showPublished = false,
    skipStepCounts = true,
}: LoadWorkflowsOptions): Promise<{ data: WorkflowSummary[]; totalMatches: number }> {
    const {
        response,
        data: workflows,
        error,
    } = await GalaxyApi().GET("/api/workflows", {
        params: {
            query: {
                sort_by: sortBy,
                sort_desc: sortDesc,
                limit,
                offset,
                search: filterText,
                show_published: showPublished,
                skip_step_counts: skipStepCounts,
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    const totalMatches = parseInt(response.headers.get("Total_matches") || "0", 10) || 0;
    const data = workflows as unknown as WorkflowSummary[];

    return { data, totalMatches };
}

export async function getWorkflowInfo(workflowId: string) {
    const { data, error } = await GalaxyApi().GET("/api/workflows/{workflow_id}", {
        params: {
            path: {
                workflow_id: workflowId,
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data;
}

export async function undeleteWorkflow(id: string): Promise<WorkflowSummary> {
    const { data, error } = await GalaxyApi().POST("/api/workflows/{workflow_id}/undelete", {
        params: {
            path: {
                workflow_id: id,
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data as WorkflowSummary;
}

export function hasCreator(entry?: AnyWorkflow): entry is StoredWorkflowDetailed {
    return entry !== undefined && "creator" in entry && !!entry.creator;
}

export function hasVersion(entry: AnyWorkflow): entry is StoredWorkflowDetailed {
    return "version" in entry;
}
