import type { WorkflowExtractionJob } from "@/api/histories";

export type ClientWorkflowExtractionJob = WorkflowExtractionJob & {
    newName?: string;
    stepType: "input_dataset" | "input_collection" | "tool";
};
