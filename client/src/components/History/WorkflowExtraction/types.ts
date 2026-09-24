import type { components } from "@/api";
import type { WorkflowExtractionJob } from "@/api/histories";

type InvalidReason = components["schemas"]["InvalidWorkflowExtractionJobReason"];
type HistoryContentType = components["schemas"]["HistoryContentType"];
type DatasetState = components["schemas"]["DatasetState"];
type ApiOutput = components["schemas"]["WorkflowExtractionOutput"];

export interface ExtractionOutput {
    id: string;
    hid: number;
    name: string;
    output_name?: string | null;
    suggested_name?: string | null;
    history_content_type: HistoryContentType;
    state: DatasetState;
    deleted: boolean;
    exposed: boolean;
    /** UI-local working label for the rename modal; empty string = no override. */
    label: string;
}

interface RowBase {
    id: string | null;
    checked: boolean;
    invalid?: InvalidReason | null;
    outputs: ExtractionOutput[];
}

export interface ToolStep extends RowBase {
    step_type: "tool";
    tool_id?: string | null;
    tool_name?: string | null;
    tool_version_warning?: string | null;
    implicit_collection_jobs_id?: string | null;
    implicit_collection_jobs_size?: number | null;
}

export interface InputStep extends RowBase {
    step_type: "input_dataset" | "input_collection";
    /** Modifiable name used for the workflow input in the generated workflow. */
    newName: string;
}

export type ExtractionRow = ToolStep | InputStep;

export function isInputStep(row: ExtractionRow): row is InputStep {
    return row.step_type !== "tool";
}

export function isMappedTool(row: ExtractionRow): row is ToolStep & { implicit_collection_jobs_id: string } {
    return row.step_type === "tool" && Boolean(row.implicit_collection_jobs_id);
}

export function toExtractionRow(job: WorkflowExtractionJob): ExtractionRow {
    const outputs = (job.outputs ?? []).map(toExtractionOutput);
    if (job.step_type === "tool") {
        return {
            id: job.id,
            checked: job.checked,
            invalid: job.invalid,
            outputs,
            step_type: "tool",
            tool_id: job.tool_id,
            tool_name: job.tool_name,
            tool_version_warning: job.tool_version_warning,
            implicit_collection_jobs_id: job.implicit_collection_jobs_id,
            implicit_collection_jobs_size: job.implicit_collection_jobs_size,
        };
    }
    return {
        id: job.id,
        checked: job.checked,
        invalid: job.invalid,
        outputs,
        step_type: job.step_type,
        newName: defaultInputName(outputs),
    };
}

function toExtractionOutput(output: ApiOutput): ExtractionOutput {
    return {
        id: output.id,
        hid: output.hid,
        name: output.name,
        output_name: output.output_name,
        suggested_name: output.suggested_name,
        history_content_type: output.history_content_type,
        state: output.state,
        deleted: output.deleted,
        exposed: output.exposed ?? false,
        label: output.suggested_name || output.name || output.output_name || "",
    };
}

function defaultInputName(outputs: ExtractionOutput[]): string {
    const first = outputs[0];
    if (!first) {
        return "";
    }
    return first.name || `Input ${first.hid}`;
}
