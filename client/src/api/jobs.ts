import type { components } from "@/api/schema";
import { ApiError, rethrowSimpleWithStatus } from "@/utils/simple-error";

import { GalaxyApi } from "./client";
import { RETRY_ON_429_HEADER } from "./client/rateLimiter";

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
    | components["schemas"]["MaxDiscoveredFilesJobMessage"]
    | components["schemas"]["OutputCollectionSecurityJobMessage"];

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
    const { data, error, response } = await GalaxyApi().DELETE("/api/jobs/{job_id}", {
        params: { path: { job_id: jobId } },
        body: message ? { message } : undefined,
        // Stopping a job is safe to repeat, so let the rate limiter retry it.
        headers: { [RETRY_ON_429_HEADER]: "1" },
    });

    if (error) {
        rethrowSimpleWithStatus(error, response);
    }

    return data;
}

/** Stops at most this many jobs at once, so bulk stops stay under proxy rate limits. */
const STOP_JOBS_CONCURRENCY = 4;

export interface StopJobsResult {
    stopped: string[];
    failed: { jobId: string; error: Error }[];
}

/**
 * Stop several jobs with bounded concurrency. The GalaxyApi rate limiter retries
 * rate-limited stops; once one gives up, queued jobs fail with its error unsent.
 * Never rejects: failures are collected per job.
 * @param onProgress Called with the number of jobs handled so far.
 */
export async function stopJobs(
    jobIds: string[],
    message?: string,
    onProgress?: (done: number) => void,
): Promise<StopJobsResult> {
    const result: StopJobsResult = { stopped: [], failed: [] };
    const queue = [...jobIds];
    let rateLimitError: Error | undefined;

    async function worker() {
        let jobId;
        while ((jobId = queue.shift()) !== undefined) {
            try {
                if (rateLimitError) {
                    throw rateLimitError;
                }
                await deleteJob(jobId, message);
                result.stopped.push(jobId);
            } catch (error) {
                const failure = error instanceof Error ? error : new Error(String(error));
                if (failure instanceof ApiError && failure.status === 429) {
                    rateLimitError = failure;
                }
                result.failed.push({ jobId, error: failure });
            }
            onProgress?.(result.stopped.length + result.failed.length);
        }
    }

    await Promise.all(Array.from({ length: Math.min(STOP_JOBS_CONCURRENCY, jobIds.length) }, worker));
    return result;
}
