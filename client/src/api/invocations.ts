import { type components } from "./schema";

export type WorkflowInvocationElementView = components["schemas"]["WorkflowInvocationElementView"];
export type WorkflowInvocationCollectionView = components["schemas"]["WorkflowInvocationCollectionView"];
export type InvocationInput = components["schemas"]["InvocationInput"];
export type InvocationInputParameter = components["schemas"]["InvocationInputParameter"];
export type InvocationJobsSummary = components["schemas"]["InvocationJobsResponse"];
export type InvocationStep = components["schemas"]["InvocationStep"];
export type InvocationMessage = components["schemas"]["InvocationMessageResponseUnion"];
export type WorkflowInvocationRequest = components["schemas"]["WorkflowInvocationRequestModel"];
export type WorkflowInvocationRequestInputs = components["schemas"]["WorkflowInvocationRequestModel"]["inputs"];

export type StepJobSummary =
    | components["schemas"]["InvocationStepJobsResponseStepModel"]
    | components["schemas"]["InvocationStepJobsResponseJobModel"]
    | components["schemas"]["InvocationStepJobsResponseCollectionJobsModel"];

export type WorkflowInvocation = components["schemas"]["WorkflowInvocationResponse"];
