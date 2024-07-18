import { type components, fetcher } from "@/api/schema";

export type JobDestinationParams = components["schemas"]["JobDestinationParams"];

export const getJobDetails = fetcher.path("/api/jobs/{job_id}").method("get").create();

export type ShowFullJobResponse = components["schemas"]["ShowFullJobResponse"];
export type JobDetails = components["schemas"]["ShowFullJobResponse"] | components["schemas"]["EncodedJobDetails"];
export const fetchJobDetails = fetcher.path("/api/jobs/{job_id}").method("get").create();

export type JobInputSummary = components["schemas"]["JobInputSummary"];
export const fetchJobCommonProblems = fetcher.path("/api/jobs/{job_id}/common_problems").method("get").create();

export const postJobErrorReport = fetcher.path("/api/jobs/{job_id}/error").method("post").create();
