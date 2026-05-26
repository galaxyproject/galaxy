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

export type JobMessage =
    | components["schemas"]["ExitCodeJobMessage"]
    | components["schemas"]["RegexJobMessage"]
    | components["schemas"]["MaxDiscoveredFilesJobMessage"];

export const NON_TERMINAL_STATES = ["new", "queued", "running", "waiting", "paused", "resubmitted", "upload"];
export const ERROR_STATES = ["error", "deleted", "deleting", "failed"];
export const TERMINAL_STATES = ["ok", "skipped", "stop", "stopping"].concat(ERROR_STATES);

interface JobDef {
    tool_id: string;
}
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
}
export interface ResponseVal {
    jobDef: JobDef;
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
