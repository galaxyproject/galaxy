import type { components } from "@/api/schema";
import type { JobsQueryParams } from "@/components/Jobs/JobsFilters";
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

/** All the states a job can be in, ordered from "just created" to "done", for display in filters. */
export const JOB_STATES: JobState[] = [
    "new",
    "resubmitted",
    "upload",
    "waiting",
    "queued",
    "running",
    "paused",
    "stop",
    "stopped",
    "ok",
    "skipped",
    "error",
    "failed",
    "deleting",
    "deleted",
];

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

/**
 * Fetch a page of jobs.
 *
 * @param offset Return jobs starting from this position
 * @param limit Maximum number of jobs to return
 * @param extraProps Additional query params, e.g. `user_id` or the filters built by `jobsFilterParams`
 * @returns A tuple of the list of jobs and the total number of matching jobs
 */
export async function fetchJobs(offset = 0, limit = 20, extraProps?: JobsQueryParams) {
    const params = {
        limit,
        offset,
        order_by: "update_time",
        ...extraProps,
    } as Record<string, unknown>;

    const { data, error, response } = await GalaxyApi().GET("/api/jobs", { params: { query: params } });

    if (error) {
        rethrowSimple(error);
    }

    const totalMatches = parseInt(response.headers.get("total_matches") ?? "0");
    return [data, totalMatches] as const;
}
