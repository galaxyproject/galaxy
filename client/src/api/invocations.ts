import axios from "axios";

import { getAppRoot } from "@/onload";

import { ApiResponse, components, fetcher } from "./schema";

// TODO: rename...
export type WorkflowInvocationSummary = components["schemas"]["WorkflowInvocationElementView"];
export type InvocationJobsSummary = components["schemas"]["InvocationJobsResponse"];
export type InvocationStep = components["schemas"]["InvocationStep"];

export const invocationsFetcher = fetcher.path("/api/invocations").method("get").create();

// TODO: Replace these interfaces with real schema models after https://github.com/galaxyproject/galaxy/pull/16707 is merged
export interface WorkflowInvocation {
    id: string;
}

export interface WorkflowInvocationJobsSummary {
    id: string;
}

export interface WorkflowInvocationStep {
    id: string;
}

export async function invocationForJob(params: { jobId: string }): Promise<WorkflowInvocation | null> {
    const { data } = await axios.get(`${getAppRoot()}api/invocations?job_id=${params.jobId}`);
    if (data.length > 0) {
        return data[0] as WorkflowInvocation;
    } else {
        return null;
    }
}

// TODO: Replace these provisional functions with fetchers after https://github.com/galaxyproject/galaxy/pull/16707 is merged
export async function fetchInvocationDetails(params: { id: string }): Promise<ApiResponse<WorkflowInvocation>> {
    const { data } = await axios.get(`${getAppRoot()}api/invocations/${params.id}`);
    return {
        data,
    } as ApiResponse<WorkflowInvocation>;
}

export async function fetchInvocationJobsSummary(params: {
    id: string;
}): Promise<ApiResponse<WorkflowInvocationJobsSummary>> {
    const { data } = await axios.get(`${getAppRoot()}api/invocations/${params.id}/jobs_summary`);
    return {
        data,
    } as ApiResponse<WorkflowInvocationJobsSummary>;
}

export async function fetchInvocationStep(params: { id: string }): Promise<ApiResponse<WorkflowInvocationStep>> {
    const { data } = await axios.get(`${getAppRoot()}api/invocations/steps/${params.id}`);
    return {
        data,
    } as ApiResponse<WorkflowInvocationStep>;
}
