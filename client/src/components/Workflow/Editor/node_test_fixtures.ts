import type { Step } from "@/stores/workflowStepStore";
import type { Connection } from "@/stores/workflowStoreTypes";

// Data terminals from tools-iuc/tools/fastqc/rgFastQC.xml (0.74+galaxy1).
export const TOOL_STEP: Step = {
    id: 0,
    name: "FastQC",
    type: "tool",
    content_id: "toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.74+galaxy1",
    input_connections: {},
    tool_state: {},
    inputs: [
        {
            name: "input_file",
            label: "Raw read data from your current history",
            multiple: false,
            optional: false,
            extensions: ["fastq", "fastq.gz", "fastq.bz2", "bam", "sam"],
            input_type: "dataset",
        },
        {
            name: "contaminants",
            label: "Contaminant list",
            multiple: false,
            optional: true,
            extensions: ["tabular"],
            input_type: "dataset",
        },
        {
            name: "adapters",
            label: "Adapter list",
            multiple: false,
            optional: true,
            extensions: ["tabular"],
            input_type: "dataset",
        },
        {
            name: "limits",
            label: "Submodule and Limit specifing file",
            multiple: false,
            optional: true,
            extensions: ["txt"],
            input_type: "dataset",
        },
    ],
    outputs: [
        { name: "html_file", extensions: ["html"], optional: false },
        { name: "text_file", extensions: ["txt"], optional: false },
    ],
    position: { top: 0, left: 0 },
};

export const SUBWORKFLOW_STEP: Step = {
    id: 0,
    name: "Quality control workflow",
    label: "Read quality control",
    type: "subworkflow",
    input_connections: {},
    tool_state: {},
    inputs: [],
    outputs: [],
    position: { top: 0, left: 0 },
};

// The server sends a missing tool's errors as a string, though `Step` types them as `string[]`.
export const MISSING_TOOL_STEP = {
    ...TOOL_STEP,
    inputs: [],
    outputs: [],
    errors: "Tool is not installed",
} as unknown as Step;

export const MISSING_TOOL_CONNECTIONS: Connection[] = [
    {
        input: { stepId: 0, name: "input1", connectorType: "input" },
        output: { stepId: 1, name: "output", connectorType: "output" },
    },
    {
        input: { stepId: 2, name: "input1", connectorType: "input" },
        output: { stepId: 0, name: "out_file1", connectorType: "output" },
    },
];
