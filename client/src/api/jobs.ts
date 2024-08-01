import { type components } from "@/api/schema";

export type JobDestinationParams = components["schemas"]["JobDestinationParams"];
export type ShowFullJobResponse = components["schemas"]["ShowFullJobResponse"];
export type JobBaseModel = components["schemas"]["JobBaseModel"];
export type JobDetails = components["schemas"]["ShowFullJobResponse"] | components["schemas"]["EncodedJobDetails"];
export type JobInputSummary = components["schemas"]["JobInputSummary"];
