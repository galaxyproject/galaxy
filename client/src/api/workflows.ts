import { components, fetcher } from "@/api/schema";

export type StoredWorkflowDetailed = components["schemas"]["StoredWorkflowDetailed"];

export const workflowsFetcher = fetcher.path("/api/workflows").method("get").create();
export const workflowFetcher = fetcher.path("/api/workflows/{workflow_id}").method("get").create();

export const invocationCountsFetcher = fetcher.path("/api/workflows/{workflow_id}/counts").method("get").create();

export const sharing = fetcher.path("/api/workflows/{workflow_id}/sharing").method("get").create();
export const enableLink = fetcher.path("/api/workflows/{workflow_id}/enable_link_access").method("put").create();
