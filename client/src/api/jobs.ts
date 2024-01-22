import { fetcher } from "@/api/schema";

export const jobLockStatus = fetcher.path("/api/job_lock").method("get").create();
export const jobLockUpdate = fetcher.path("/api/job_lock").method("put").create();
