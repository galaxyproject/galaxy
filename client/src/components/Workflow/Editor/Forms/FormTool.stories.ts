import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withLoadedConfig } from "@tests/test-data/config";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { HttpResponse } from "msw";
import { h, toRaw } from "vue";

import { configurationHandler, http } from "@/api/client/__mocks__/http";
import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";

import { withWorkflowStores } from "../test_fixtures";

import FormTool from "./FormTool.vue";

const FASTQC_ID = "toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.72+galaxy1";

/** A FastQC step at the oldest of its three versions, as the editor loads it. */
const FASTQC_STEP = {
    id: 1,
    type: "tool",
    name: "FastQC",
    content_id: FASTQC_ID,
    tool_version: "0.72+galaxy1",
    label: null,
    annotation: "",
    config_form: {
        id: FASTQC_ID,
        name: "FastQC",
        version: "0.72+galaxy1",
        description: "Read Quality reports",
        versions: ["0.72+galaxy1", "0.73+galaxy0", "0.74+galaxy1"],
        inputs: [
            {
                name: "input_file",
                label: "Raw read data from your current history",
                type: "data",
                extensions: ["fastqsanger", "fastqsanger.gz", "bam", "sam"],
            },
            {
                name: "min_length",
                label: "Lower limit on the length of the sequence to be shown in the report",
                type: "integer",
                value: "",
                optional: true,
            },
        ],
        help: "<p><strong>What it does</strong></p><p>FastQC runs quality control checks on raw sequence data.</p>",
        help_format: "restructuredtext",
        citations: false,
    },
    inputs: [
        {
            name: "input_file",
            label: "Raw read data from your current history",
            extensions: ["fastqsanger", "fastqsanger.gz", "bam", "sam"],
        },
    ],
    outputs: [
        { name: "html_file", extensions: ["html"], optional: false },
        { name: "text_file", extensions: ["txt"], optional: false },
    ],
    post_job_actions: {},
    input_connections: {},
    workflow_outputs: [],
};

/** A rule-builder value: name each element by its identifier, after adding the identifier as a column. */
const RULES_VALUE = {
    mapping: [{ type: "list_identifiers", columns: [1] }],
    rules: [{ type: "add_column_metadata", value: "identifier0" }],
};

/**
 * A step of Galaxy's `gx_rules` parameter test tool, given a text parameter beside its rules one to show
 * that the form's rules handling leaves a sibling alone. No shipped tool pairs the two.
 */
const RULES_STEP = {
    id: 2,
    type: "tool",
    name: "gx_rules",
    content_id: "gx_rules",
    tool_version: "1.0.0",
    label: null,
    annotation: "",
    config_form: {
        id: "gx_rules",
        name: "gx_rules",
        version: "1.0.0",
        description: "",
        versions: ["1.0.0"],
        inputs: [
            { name: "prefix", label: "Identifier prefix", type: "text", value: "sample_" },
            { name: "parameter", label: "Rules", type: "rules", value: RULES_VALUE },
        ],
        help: "",
        help_format: "restructuredtext",
        citations: false,
    },
    inputs: [],
    outputs: [{ name: "output", extensions: ["txt"], optional: false }],
    post_job_actions: {},
    input_connections: {},
    workflow_outputs: [],
};

/** A tool step's form in the workflow editor's side panel: label, annotation, tool parameters and output options. */
const meta = {
    title: "Workflow/Editor/Forms/FormTool",
    component: FormTool,
    // The form marks its step's inputs in place, so each render gets its own copy of the step.
    render: (args) => () => h(FormTool, { ...args, step: structuredClone(toRaw(args.step)) }),
    decorators: [withLoadedConfig, withWorkflowStores("f2db41e1fa331b3e"), withCurrentUser()],
    args: { step: FASTQC_STEP, datatypes: testDatatypesMapper.datatypes },
    parameters: {
        msw: {
            handlers: {
                configuration: configurationHandler({ enable_tool_source_display: false }),
                webhooks: http.untyped.get("/api/webhooks", () => HttpResponse.json([])),
            },
        },
    },
} satisfies Meta<typeof FormTool>;

export default meta;
type Story = StoryObj<typeof meta>;

/** FastQC at an older version: the versions menu offers the two newer ones. */
export const OlderToolVersion: Story = {};

/** A tool with a rules parameter, which stays set in advance, beside a text one that can be set at runtime. */
export const RulesParameter: Story = { args: { step: RULES_STEP } };
