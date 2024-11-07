import { type components } from "./schema";

export type WorkflowInvocationElementView = components["schemas"]["WorkflowInvocationElementView"];
export type LegacyWorkflowInvocationElementView = components["schemas"]["LegacyWorkflowInvocationElementView"];
export type WorkflowInvocationCollectionView = components["schemas"]["WorkflowInvocationCollectionView"];
export type WorkflowInvocationStepStatesView = components["schemas"]["WorkflowInvocationStepStatesView"];
export type InvocationJobsSummary = components["schemas"]["InvocationJobsResponse"];
export type InvocationStep = components["schemas"]["InvocationStep"];
export type LegacyInvocationStep = components["schemas"]["LegacyInvocationStep"];
export type InvocationMessage = components["schemas"]["InvocationMessageResponseUnion"];

export type StepJobSummary =
    | components["schemas"]["InvocationStepJobsResponseStepModel"]
    | components["schemas"]["InvocationStepJobsResponseJobModel"]
    | components["schemas"]["InvocationStepJobsResponseCollectionJobsModel"];

export type WorkflowInvocation = components["schemas"]["WorkflowInvocationResponse"];
