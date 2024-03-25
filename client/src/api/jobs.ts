import { components, fetcher } from "@/api/schema";

export type JobDestinationParams = components["schemas"]["JobDestinationParams"];

export const getJobDetails = fetcher.path("/api/jobs/{job_id}").method("get").create();

export const jobLockStatus = fetcher.path("/api/job_lock").method("get").create();
export const jobLockUpdate = fetcher.path("/api/job_lock").method("put").create();

export const fetchJobDestinationParams = fetcher.path("/api/jobs/{job_id}/destination_params").method("get").create();

export const jobsFetcher = fetcher.path("/api/jobs").method("get").create();

export type ShowFullJobResponse = components["schemas"]["ShowFullJobResponse"];
export type JobDetails = components["schemas"]["ShowFullJobResponse"] | components["schemas"]["EncodedJobDetails"];
export const fetchJobDetails = fetcher.path("/api/jobs/{job_id}").method("get").create();

export type JobInputSummary = components["schemas"]["JobInputSummary"];
export const fetchJobCommonProblems = fetcher.path("/api/jobs/{job_id}/common_problems").method("get").create();

export const postJobErrorReport = fetcher.path("/api/jobs/{job_id}/error").method("post").create();
