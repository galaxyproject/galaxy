import { type components, fetcher } from "@/api/schema";

export type StoredWorkflowDetailed = components["schemas"]["StoredWorkflowDetailed"];

export const workflowFetcher = fetcher.path("/api/workflows/{workflow_id}").method("get").create();

export const invocationCountsFetcher = fetcher.path("/api/workflows/{workflow_id}/counts").method("get").create();

export const sharing = fetcher.path("/api/workflows/{workflow_id}/sharing").method("get").create();
export const enableLink = fetcher.path("/api/workflows/{workflow_id}/enable_link_access").method("put").create();

//TODO: replace with generated schema model when available
export interface WorkflowSummary {
    name: string;
    owner: string;
    [key: string]: unknown;
    update_time: string;
    license?: string;
    tags?: string[];
    creator?: {
        [key: string]: unknown;
    }[];
}
