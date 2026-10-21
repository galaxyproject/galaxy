import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { expect } from "storybook/test";

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
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

async function readReadme({ canvas }: PlayContext) {
    const bold = await canvas.findByText("Readme", { exact: true });
    await expect(bold).toBeVisible();
    await expect(bold.tagName).toBe("STRONG");
    const paragraph = bold.parentElement!;
    await expect(paragraph).toHaveTextContent(/^Readme with a link and <em>raw<\/em>$/);
    const link = canvas.getByRole("link", { name: "a link" });
    await expect(link).toBeVisible();
    await expect(link).toHaveAttribute("href", "https://galaxyproject.org");
    await expect(link).toHaveAttribute("target", "_blank");
    await expect(canvas.queryByText("raw", { exact: true })).not.toBeInTheDocument();
    return paragraph;
}

async function readHelp({ canvas }: PlayContext) {
    const heading = await canvas.findByRole("heading", { name: "Workflow Help" });
    await expect(heading).toBeVisible();
    const emphasis = canvas.getByRole("emphasis");
    await expect(emphasis).toBeVisible();
    await expect(emphasis.tagName).toBe("EM");
    await expect(emphasis).toHaveTextContent(/^text$/);
    const paragraph = emphasis.parentElement!;
    await expect(paragraph).toHaveTextContent(/^Help text$/);
    return { heading, paragraph };
}

function expectBefore(first: Element, second: Element) {
    expect(first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING).toBe(
        Node.DOCUMENT_POSITION_FOLLOWING,
    );
}

/** The workflow author's README and run instructions; external links open in a new tab and raw HTML stays literal. */
export const ReadmeAndHelp: Story = {
    play: async (context) => {
        await context.step("Read the README before the run-help section", async () => {
            const readme = await readReadme(context);
            const { heading, paragraph } = await readHelp(context);
            const end = context.canvas.getByText("- End of help -", { exact: true });
            await expect(end).toBeVisible();
            expectBefore(readme, heading);
            expectBefore(heading, paragraph);
            expectBefore(paragraph, end);
        });
    },
};

/** A workflow with a README and no separate run-help section. */
export const ReadmeOnly: Story = {
    args: { workflow: { ...DOCUMENTED_WORKFLOW, help: null } },
    play: async (context) => {
        await context.step("Read only the README without an empty help section", async () => {
            await readReadme(context);
            await expect(context.canvas.getByText("- End of help -", { exact: true })).toBeVisible();
            await expect(context.canvas.queryByRole("heading", { name: "Workflow Help" })).not.toBeInTheDocument();
            await expect(context.canvas.queryByRole("emphasis")).not.toBeInTheDocument();
        });
    },
};

/** Run instructions without a README. */
export const HelpOnly: Story = {
    args: { workflow: { ...DOCUMENTED_WORKFLOW, readme: null } },
    play: async (context) => {
        await context.step("Read only the run-help section without a README", async () => {
            await readHelp(context);
            await expect(context.canvas.getByText("- End of help -", { exact: true })).toBeVisible();
            await expect(context.canvas.queryByText("Readme", { exact: true })).not.toBeInTheDocument();
            await expect(context.canvas.queryByRole("link")).not.toBeInTheDocument();
        });
    },
};

/** The workflow's details are still loading, so its documentation is not shown yet. */
export const Loading: Story = {
    args: { loading: true },
    play: async ({ canvas, step }) => {
        await step("Read the loading state without stale documentation", async () => {
            const loading = await canvas.findByRole("status");
            await expect(loading).toBeVisible();
            await expect(loading).toHaveTextContent(/^Loading workflow help\.\.\.$/);
            await expect(canvas.queryByText("Readme", { exact: true })).not.toBeInTheDocument();
            await expect(canvas.queryByRole("heading", { name: "Workflow Help" })).not.toBeInTheDocument();
            await expect(canvas.queryByRole("link")).not.toBeInTheDocument();
            await expect(canvas.queryByText("- End of help -", { exact: true })).not.toBeInTheDocument();
        });
    },
};
