import type { components } from "@/api/schema";

export type JobDestinationParams = components["schemas"]["JobDestinationParams"];
export type ShowFullJobResponse = components["schemas"]["ShowFullJobResponse"];
export type JobBaseModel = components["schemas"]["JobBaseModel"];
export type JobDetails = components["schemas"]["ShowFullJobResponse"] | components["schemas"]["EncodedJobDetails"];
export type JobInputSummary = components["schemas"]["JobInputSummary"];
export type JobDisplayParametersSummary = components["schemas"]["JobDisplayParametersSummary"];
export type JobMetric = components["schemas"]["JobMetric"];

export const NON_TERMINAL_STATES = ["new", "queued", "running", "waiting", "paused", "resubmitted", "stop"];
export const ERROR_STATES = ["error", "deleted", "deleting"];
export const TERMINAL_STATES = ["ok", "skipped", "stop", "stopping", "skipped"].concat(ERROR_STATES);

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
