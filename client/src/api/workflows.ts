import { fetcher } from "@/api/schema";

export const workflowsFetcher = fetcher.path("/api/workflows").method("get").create();

export const invocationCountsFetcher = fetcher.path("/api/workflows/{workflow_id}/counts").method("get").create();
