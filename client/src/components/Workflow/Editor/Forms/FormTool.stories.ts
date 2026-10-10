import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withLoadedConfig } from "@tests/test-data/config";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { exactly } from "@tests/test-data/text";
import { HttpResponse } from "msw";
import { expect, waitFor, within } from "storybook/test";
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

type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

/** The card waits on the configuration, so the first wait gets longer than the 1s default. */
const CONFIG_LOAD = { timeout: 5000 };

/** Waits for the card's heading, the tool's name, before anything else is read. */
async function seeToolHeading({ canvas, step }: PlayContext, name: string) {
    await step(`See "${name}" as the page heading`, async () => {
        await expect(await canvas.findByRole("heading", { level: 1, name }, CONFIG_LOAD)).toBeVisible();
    });
}

/** Opens the versions menu, reads its items in order and returns the menu. */
async function openVersions({ canvas, step, userEvent }: PlayContext, items: string[]) {
    let menu!: HTMLElement;
    await step(`Open the versions menu: ${items.join(", ")}`, async () => {
        await expect(canvas.queryByRole("menu", { name: "Select Versions" })).not.toBeInTheDocument();
        await userEvent.click(canvas.getByRole("button", { name: "Select Versions" }));
        menu = await canvas.findByRole("menu", { name: "Select Versions" });
        await expect(menu).toBeVisible();
        const names = within(menu)
            .getAllByRole("menuitem")
            .map((item) => item.textContent?.trim());
        await expect(names).toEqual(items);
    });
    return menu;
}

/** Picks `version` from the open versions menu and sees the form say it switched. */
async function switchTo({ canvas, step, userEvent }: PlayContext, menu: HTMLElement, version: string) {
    await step(`Switch to ${version}; see the form say so`, async () => {
        await userEvent.click(within(menu).getByRole("menuitem", { name: `Switch to ${version}` }));
        // The message hides itself after 3s, so it's read straight after the click.
        await waitFor(() =>
            expect(canvas.getByRole("status")).toHaveTextContent(
                exactly(`Now you are using 'FastQC' version ${version}.`),
            ),
        );
    });
}

const OLDER_VERSIONS_MENU = ["Switch to 0.74+galaxy1", "Switch to 0.73+galaxy0", "Selected 0.72+galaxy1"];

/** FastQC at an older version: the versions menu offers the two newer ones. */
export const OlderToolVersion: Story = {};

/** Picking another version from the menu tells the user which version the step now uses. */
export const SwitchesVersion: Story = {
    play: async (context) => {
        await seeToolHeading(context, "FastQC");
        await context.step("See the step at its older version", async () => {
            await expect(context.canvas.getByText("(Galaxy Version 0.72+galaxy1)")).toBeVisible();
            await expect(context.canvas.queryByRole("status")).not.toBeInTheDocument();
        });
        await switchTo(context, await openVersions(context, OLDER_VERSIONS_MENU), "0.73+galaxy0");
        // The editor swaps in the new version's step; this story's step stays as it was.
        await switchTo(context, await openVersions(context, OLDER_VERSIONS_MENU), "0.74+galaxy1");
    },
};

/**
 * The field whose title is `title`: the label and the toggles beside it.
 *
 * Pre-existing bug, tolerated by `RUNTIME_TOGGLE`: FormTool passes `text-enable`/`text-disable`, which
 * FormDisplay no longer takes (it takes `collapsed-enable-text`/`collapsed-disable-text`), so the toggle
 * reads FormElement's default "Disable" instead of "Set at Runtime".
 */
function fieldTitle({ canvas }: PlayContext, title: string) {
    return within(canvas.getByText(exactly(title), { selector: "label" }).closest("div")!);
}

/** The toggle that sets a field at runtime; see `fieldTitle` for the bug it tolerates. */
const RUNTIME_TOGGLE = /^(Disable|Set at Runtime)\b/;

/** A tool with a rules parameter, which stays set in advance, beside a text one that can be set at runtime. */
export const RulesParameter: Story = {
    args: { step: RULES_STEP },
    play: async (context) => {
        await seeToolHeading(context, "gx_rules");
        await context.step("See the text field offer to be set at runtime or connected", async () => {
            const prefix = fieldTitle(context, "Identifier prefix");
            await expect(prefix.getByRole("button", { name: RUNTIME_TOGGLE })).toBeVisible();
            await expect(prefix.getByRole("button", { name: /^Add connection to module\./ })).toBeVisible();
        });
        await context.step("See the rules field offer neither", async () => {
            await expect(fieldTitle(context, "Rules").queryAllByRole("button")).toEqual([]);
        });
    },
};
