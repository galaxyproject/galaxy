import axios from "axios";

import { getAppRoot } from "@/onload";

import { ApiResponse } from "./schema";

// TODO: Replace these interfaces with real schema models after https://github.com/galaxyproject/galaxy/pull/16707 is merged
export interface WorkflowInvocationDetails {
    id: string;
}

export interface WorkflowInvocationJobsSummary {
    id: string;
}

export interface WorkflowInvocationStep {
    id: string;
}

// TODO: Replace these provisional functions with fetchers after https://github.com/galaxyproject/galaxy/pull/16707 is merged
export async function fetchInvocationDetails(params: { id: string }): Promise<ApiResponse<WorkflowInvocationDetails>> {
    const { data } = await axios.get(`${getAppRoot()}api/invocations/${params.id}`);
    return {
        data,
    } as ApiResponse<WorkflowInvocationDetails>;
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
    const { data } = await axios.get(`${getAppRoot()}api/invocations//any/steps/${params.id}`);
    return {
        data,
    } as ApiResponse<WorkflowInvocationStep>;
}
