import { components, fetcher } from "@/api/schema";

export type JobDestinationParams = components["schemas"]["JobDestinationParams"];

export const jobLockStatus = fetcher.path("/api/job_lock").method("get").create();
export const jobLockUpdate = fetcher.path("/api/job_lock").method("put").create();

export const fetchJobDestinationParams = fetcher.path("/api/jobs/{job_id}/destination_params").method("get").create();

export const jobsFetcher = fetcher.path("/api/jobs").method("get").create();
