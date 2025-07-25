import type { FreehandWorkflowComment, WorkflowComment } from "@/stores/workflowEditorCommentStore";
import type { Step } from "@/stores/workflowStepStore";

import type { Workflow } from "../modules/model";

export function mockToolStep(id: number): Step {
    return {
        id,
        type: "tool",
        label: null,
        content_id: "cat1",
        name: "Concatenate datasets",
        tool_state: {
            input1: '{"__class__": "ConnectedValue"}',
            queries: "[]",
            __page__: null,
            __rerun_remap_job_id__: null,
        },
        errors: null,
        inputs: [
            {
                name: "input1",
                label: "Concatenate Dataset",
                multiple: false,
                extensions: ["data"],
                optional: false,
                input_type: "dataset",
            },
        ],
        outputs: [{ name: "out_file1", extensions: ["input"], type: "data", optional: false }],
        config_form: {
            model_class: "Tool",
            id: "cat1",
            name: "Concatenate datasets",
            version: "1.0.0",
            description: "tail-to-head",
            labels: [],
            edam_operations: ["operation_3436"],
            edam_topics: [],
            hidden: "",
            is_workflow_compatible: true,
            xrefs: [],
            config_file: "/path/to/file",
            panel_section_id: "textutil",
            panel_section_name: "Text Manipulation",
            form_style: "regular",
            inputs: [
                {
                    model_class: "DataToolParameter",
                    name: "input1",
                    argument: null,
                    type: "data",
                    label: "Concatenate Dataset",
                    help: "",
                    refresh_on_change: true,
                    optional: false,
                    hidden: false,
                    is_dynamic: false,
                    value: { __class__: "ConnectedValue" },
                    extensions: ["data"],
                    edam: { edam_formats: ["format_1915"], edam_data: ["data_0006"] },
                    multiple: false,
                    options: { dce: [], ldda: [], hda: [], hdca: [] },
                    tag: null,
                    default_value: { __class__: "RuntimeValue" },
                    text_value: "Not available.",
                },
                {
                    model_class: "Repeat",
                    name: "queries",
                    type: "repeat",
                    title: "Dataset",
                    help: null,
                    default: 0,
                    min: 0,
                    max: "__Infinity__",
                    inputs: [
                        {
                            model_class: "DataToolParameter",
                            name: "input2",
                            argument: null,
                            type: "data",
                            label: "Select",
                            help: "",
                            refresh_on_change: true,
                            optional: false,
                            hidden: false,
                            is_dynamic: false,
                            value: { __class__: "RuntimeValue" },
                            extensions: ["data"],
                            edam: { edam_formats: ["format_1915"], edam_data: ["data_0006"] },
                            multiple: false,
                            options: { dce: [], ldda: [], hda: [], hdca: [] },
                            tag: null,
                        },
                    ],
                    cache: [],
                },
            ],
            help: "tool help",
            citations: false,
            sharable_url: null,
            message: "",
            warnings: null,
            versions: ["1.0.0"],
            requirements: [],
            errors: {},
            tool_errors: null,
            state_inputs: { input1: { __class__: "ConnectedValue" }, queries: [] },
            job_id: null,
            job_remap: null,
            history_id: null,
            display: true,
            action: "/tool_runner/index",
            license: null,
            creator: null,
            method: "post",
            enctype: "application/x-www-form-urlencoded",
        },
        annotation: "",
        post_job_actions: {},
        uuid: `fake-uuid-${id}`,
        when: null,
        workflow_outputs: [],
        tooltip: "tip",
        tool_version: "1.0.0",
        input_connections: { input1: [{ output_name: "output", id: 0 }] },
        position: { left: 300, top: 100 },
    };
}

const inputStep = {
    id: 0,
    type: "data_input",
    label: null,
    content_id: null,
    name: "Input dataset",
    tool_state: { optional: "false", tag: null, __page__: null, __rerun_remap_job_id__: null },
    errors: null,
    inputs: [],
    outputs: [{ name: "output", extensions: ["input"], optional: false }],
    config_form: {
        title: "Input dataset",
        inputs: [
            {
                model_class: "BooleanToolParameter",
                name: "optional",
                argument: null,
                type: "boolean",
                label: "Optional",
                help: null,
                refresh_on_change: false,
                optional: false,
                hidden: false,
                is_dynamic: false,
                value: false,
                truevalue: "true",
                falsevalue: "false",
            },
            {
                model_class: "TextToolParameter",
                name: "format",
                argument: null,
                type: "text",
                label: "Format(s)",
                help: "Leave empty to auto-generate filtered list at runtime based on connections.",
                refresh_on_change: false,
                optional: true,
                hidden: false,
                is_dynamic: false,
                value: "",
                area: false,
                datalist: [],
            },
            {
                model_class: "TextToolParameter",
                name: "tag",
                argument: null,
                type: "text",
                label: "Tag filter",
                help: "Tags to automatically filter inputs",
                refresh_on_change: false,
                optional: true,
                hidden: false,
                is_dynamic: false,
                value: null,
                area: false,
                datalist: [],
            },
        ],
    },
    annotation: "",
    post_job_actions: {},
    uuid: "8ecca4e7-a50e-4e96-a038-7b735e93b54f",
    when: null,
    workflow_outputs: [],
    tooltip: null,
    input_connections: {},
    position: { left: 0, top: 100 },
} as Step;

export function mockWorkflow(): Workflow {
    return {
        name: "Mock Workflow",
        annotation: "this is not a real workflow",
        comments: [],
        creator: [],
        license: "",
        report: {
            markdown: "",
        },
        steps: {
            "0": structuredClone(inputStep),
        },
        tags: [],
        version: 1,
    };
}

export function mockComment(id: number): WorkflowComment {
    return {
        id,
        position: [0, 0],
        size: [170, 50],
        type: "text",
        color: "none",
        data: { size: 2, text: "Enter Text" },
    };
}

export function mockFreehandComment(id: number): FreehandWorkflowComment {
    return {
        id,
        position: [0, 0],
        size: [100, 200],
        type: "freehand",
        color: "none",
        data: {
            thickness: 1,
            line: [
                [0, 0],
                [10, 20],
                [100, 200],
            ],
        },
    };
}
