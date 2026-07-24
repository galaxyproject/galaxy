import type { components } from "@/api/schema";
import { rethrowSimple } from "@/utils/simple-error";

import { GalaxyApi } from "./client";

export type CuratedWorkflow = components["schemas"]["CuratedWorkflow"];
export type CuratedWorkflowsIndexResponse = components["schemas"]["CuratedWorkflowsIndexResponse"];
export type CuratedWorkflowSource = CuratedWorkflowsIndexResponse["source"];

export type CuratedWorkflowSortBy = "create_time" | "update_time" | "name";

interface LoadCuratedWorkflowsOptions {
    search?: string;
    sortBy?: CuratedWorkflowSortBy;
    sortDesc?: boolean;
    limit: number;
    offset: number;
}

/**
 * Fetches a page of curated workflows.
 *
 * The response always carries a `source` discriminator, including for the
 * `preparing` and `unavailable` states, which arrive as a normal 200 rather
 * than as errors.
 */
export async function loadCuratedWorkflows({
    search,
    sortBy,
    sortDesc,
    limit,
    offset,
}: LoadCuratedWorkflowsOptions): Promise<CuratedWorkflowsIndexResponse> {
    const { data, error } = await GalaxyApi().GET("/api/workflows/curated", {
        params: {
            query: {
                search,
                sort_by: sortBy,
                sort_desc: sortDesc,
                limit,
                offset,
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data;
}
