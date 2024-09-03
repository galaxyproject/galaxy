import { type components } from "@/api/schema";

export type StoredWorkflowDetailed = components["schemas"]["StoredWorkflowDetailed"];

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
