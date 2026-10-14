import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentUser } from "@tests/test-data/currentUser";

import { OWN_WORKFLOW, SIGNED_IN_USER } from "../test_fixtures";

import WorkflowHelpDisplay from "./WorkflowHelpDisplay.vue";

const DOCUMENTED_WORKFLOW = {
    ...OWN_WORKFLOW,
    name: "RNA-seq quality control",
    readme: "**Readme** with [a link](https://galaxyproject.org) and <em>raw</em>",
    help: "Help *text*",
};

const meta = {
    title: "Workflow/Run/WorkflowHelpDisplay",
    component: WorkflowHelpDisplay,
    decorators: [withCurrentUser(() => SIGNED_IN_USER)],
    args: { workflow: DOCUMENTED_WORKFLOW },
} satisfies Meta<typeof WorkflowHelpDisplay>;

export default meta;
type Story = StoryObj<typeof meta>;

/** The workflow author's README and run instructions; external links open in a new tab and raw HTML stays literal. */
export const ReadmeAndHelp: Story = {};

/** A workflow with a README and no separate run-help section. */
export const ReadmeOnly: Story = {
    args: { workflow: { ...DOCUMENTED_WORKFLOW, help: null } },
};

/** Run instructions without a README. */
export const HelpOnly: Story = {
    args: { workflow: { ...DOCUMENTED_WORKFLOW, readme: null } },
};

/** The workflow's details are still loading, so its documentation is not shown yet. */
export const Loading: Story = {
    args: { loading: true },
};
