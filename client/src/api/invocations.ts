import { rethrowSimple } from "@/utils/simple-error";

import { GalaxyApi } from "./client";
import type { components } from "./schema";

export type WorkflowInvocationElementView = components["schemas"]["WorkflowInvocationElementView"];
export type WorkflowInvocationCollectionView = components["schemas"]["WorkflowInvocationCollectionView"];
export type InvocationInput = components["schemas"]["InvocationInput"];
export type InvocationInputParameter = components["schemas"]["InvocationInputParameter"];
export type InvocationOutput = components["schemas"]["InvocationOutput"];
export type InvocationOutputCollection = components["schemas"]["InvocationOutputCollection"];
export type InvocationJobsSummary = components["schemas"]["InvocationJobsResponse"];
type InvocationReport = components["schemas"]["InvocationReport"];
export type InvocationState = components["schemas"]["InvocationState"];
export type InvocationStep = components["schemas"]["InvocationStep"];
export type InvocationMessage = components["schemas"]["InvocationMessageResponseUnion"];
export type WorkflowInvocationRequest = components["schemas"]["WorkflowInvocationRequestModel"];
export type WorkflowInvocationRequestInputs = components["schemas"]["WorkflowInvocationRequestModel"]["inputs"];

export type StepJobSummary =
    | components["schemas"]["InvocationStepJobsResponseStepModel"]
    | components["schemas"]["InvocationStepJobsResponseJobModel"]
    | components["schemas"]["InvocationStepJobsResponseCollectionJobsModel"];

export type WorkflowJobMetric = components["schemas"]["WorkflowJobMetric"];

export type WorkflowInvocation = components["schemas"]["WorkflowInvocationResponse"];

export function isWorkflowInvocationElementView(
    item: WorkflowInvocation | null,
): item is WorkflowInvocationElementView {
    return item !== null && "steps" in item;
}

// TODO: Consider caching this in the store given this doesn't change as it is generated once
// when an invocation is complete?
/**
 * Fetches the invocation report for a given invocation ID
 * @param {string} invocationId The ID of the invocation to fetch the report for
 * @returns {Promise<InvocationReport>} A promise that resolves to the invocation report
 */
export async function fetchInvocationReport(invocationId: string): Promise<InvocationReport> {
    const { data, error } = await GalaxyApi().GET("/api/invocations/{invocation_id}/report", {
        params: {
            path: { invocation_id: invocationId },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data as InvocationReport;
}

/**
 * Fetches the workflow invocation associated with a given job ID
 * @param {string} jobId The ID of the job to fetch the invocation for
 * @returns {Promise<WorkflowInvocation | null>} A promise that resolves to the workflow invocation
 * or `null` if not found (could mean that the job is not part of any workflow invocation)
 */
export async function fetchInvocationForJob(jobId: string): Promise<WorkflowInvocation | null> {
    const { data: invocations, error } = await GalaxyApi().GET("/api/invocations", {
        params: {
            query: { job_id: jobId },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    if (invocations.length && invocations[0]) {
        return invocations[0];
    }

    return null;
}
