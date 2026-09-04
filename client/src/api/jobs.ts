import type { components } from "@/api/schema";
import { rethrowSimple } from "@/utils/simple-error";

import { GalaxyApi } from "./client";

export type JobDestinationParams = components["schemas"]["JobDestinationParams"];
export type ShowFullJobResponse = components["schemas"]["ShowFullJobResponse"];
export type JobBaseModel = components["schemas"]["JobBaseModel"];
export type JobState = components["schemas"]["JobState"];
export type JobConsoleOutput = components["schemas"]["JobConsoleOutput"];
export type JobDetails = components["schemas"]["ShowFullJobResponse"] | components["schemas"]["EncodedJobDetails"];
export type JobInputSummary = components["schemas"]["JobInputSummary"];
export type JobDisplayParametersSummary = components["schemas"]["JobDisplayParametersSummary"];
export type JobMetric = components["schemas"]["JobMetric"];
export type JobRequest = components["schemas"]["JobRequest"];

export type JobMessage =
    | components["schemas"]["ExitCodeJobMessage"]
    | components["schemas"]["RegexJobMessage"]
    | components["schemas"]["MaxDiscoveredFilesJobMessage"]
    | components["schemas"]["OutputCollectionSecurityJobMessage"];

export const NON_TERMINAL_STATES = ["new", "queued", "running", "waiting", "paused", "resubmitted", "upload"];
export const ERROR_STATES = ["error", "deleted", "deleting", "failed"];
export const TERMINAL_STATES = ["ok", "skipped", "stop", "stopping"].concat(ERROR_STATES);

export interface JobResponse {
    produces_entry_points: boolean;
    jobs: Array<JobBaseModel | ShowFullJobResponse>;
    outputs: {
        hid: number;
        name: string;
    }[]; // TODO: This is temporary, adjust when API response is typed
    output_collections: {
        hid: number;
        name: string;
    }[]; // TODO: This is temporary, adjust when API response is typed
    // implicit_collections // TODO: Add when API response is typed
    errors?: any;
}
export interface ResponseVal {
    jobDef: JobRequest;
    jobResponse: JobResponse;
    toolName: string;
}

/**
 * Delete/Stop a job.
 * @param jobId The ID of the job to delete.
 * @param message An optional message to be set on the job and output dataset(s) to explain the reason for stopping.
 * @returns A promise that resolves to a boolean indicating whether the job was successfully deleted or job was already in a terminal state.
 */
export async function deleteJob(jobId: string, message?: string): Promise<boolean> {
    const { data, error } = await GalaxyApi().DELETE("/api/jobs/{job_id}", {
        params: { path: { job_id: jobId } },
        data: { message },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data;
}

/**
 * Fetch the outputs of a job.
 * @param jobId The ID of the job whose outputs are to be fetched.
 * @returns A promise that resolves to the dataset or dataset collection outputs of the job.
 */
export async function fetchJobOutputs(jobId: string) {
    const { data, error } = await GalaxyApi().GET("/api/jobs/{job_id}/outputs", {
        params: { path: { job_id: jobId } },
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

/**
 * Submit a job request (for Celery enabled tool requests).
 * @param jobRequest Job request object containing the details of the job to be submitted.
 * @returns A promise that resolves to the `task_result` and `tool_request_id` of the submitted job.
 */
export async function submitJobRequest(jobRequest: JobRequest) {
    const { data, error } = await GalaxyApi().POST("/api/jobs", {
        body: jobRequest,
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}
