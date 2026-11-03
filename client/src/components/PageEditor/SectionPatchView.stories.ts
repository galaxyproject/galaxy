import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { exactly } from "@tests/test-data/text";
import { expect, fn } from "storybook/test";

import { PAGE_ORIGINAL_SECTIONS, PAGE_PROPOSED_SECTIONS } from "./testData";

import SectionPatchView from "./SectionPatchView.vue";

const meta = {
    title: "PageEditor/SectionPatchView",
    component: SectionPatchView,
    decorators: [withCurrentUser()],
    args: {
        original: PAGE_ORIGINAL_SECTIONS,
        proposed: PAGE_PROPOSED_SECTIONS,
        onAccept: fn(),
        onReject: fn(),
    },
} satisfies Meta<typeof SectionPatchView>;

export default meta;
type Story = StoryObj<typeof meta>;

export const TwoSectionProposal: Story = {};

export const SingleSectionProposal: Story = {
    args: { original: "# Results\nExpression counts pending.", proposed: "# Results\nExpression counts ready." },
};

export const UnchangedProposal: Story = {
    args: { original: "# Methods\nReads aligned with STAR.", proposed: "# Methods\nReads aligned with STAR." },
};

export const StaleProposal: Story = { args: { stale: true } };

export const SelectsSectionsToApply: Story = {
    play: async ({ canvas, userEvent, step }) => {
        const label = (name: string) => {
            const checkbox = canvas.getByRole("checkbox", { name }) as HTMLInputElement;
            const associatedLabel = checkbox.labels?.[0];
            if (!associatedLabel) {
                throw new Error(`No visible label for section ${name}.`);
            }
            return associatedLabel;
        };
        const summary = () => canvas.getByText(/^2 sections changed/);
        const apply = (count: number) => canvas.getByRole("button", { name: `Apply (${count})` });
        await step("Review the two changed sections before selecting either", async () => {
            await expect(summary()).toHaveTextContent(exactly("2 sections changed"));
            await expect(label("# Intro")).toBeVisible();
            await expect(label("# Results")).toBeVisible();
            await expect(canvas.queryByRole("checkbox", { name: "# Methods" })).not.toBeInTheDocument();
            await expect(canvas.getByRole("checkbox", { name: "# Intro" })).not.toBeChecked();
            await expect(canvas.getByRole("checkbox", { name: "# Results" })).not.toBeChecked();
            await expect(apply(0)).toHaveAttribute("aria-disabled", "true");
            for (const line of [
                "- Analysis of paired-end RNA-seq reads.",
                "+ Analysis of paired-end RNA-seq reads after adapter trimming.",
                "- Expression counts pending.",
                "+ Expression counts ready.",
            ]) {
                await expect(canvas.getByText(line, { exact: true })).toBeVisible();
            }
        });
        await step("Choose Intro and then Results", async () => {
            await userEvent.click(label("# Intro"));
            await expect(summary()).toHaveTextContent(exactly("2 sections changed · 1 selected"));
            await expect(apply(1)).not.toHaveAttribute("aria-disabled", "true");
            await userEvent.click(label("# Results"));
            await expect(summary()).toHaveTextContent(exactly("2 sections changed · 2 selected"));
            await expect(apply(2)).not.toHaveAttribute("aria-disabled", "true");
        });
        await step("Leave only Results selected", async () => {
            await userEvent.click(label("# Intro"));
            await expect(summary()).toHaveTextContent(exactly("2 sections changed · 1 selected"));
            await expect(apply(1)).not.toHaveAttribute("aria-disabled", "true");
        });
        await step("Select all changed sections, then clear the selection", async () => {
            await userEvent.click(canvas.getByRole("button", { name: "All" }));
            await expect(canvas.getByRole("checkbox", { name: "# Intro" })).toBeChecked();
            await expect(canvas.getByRole("checkbox", { name: "# Results" })).toBeChecked();
            await expect(summary()).toHaveTextContent(exactly("2 sections changed · 2 selected"));
            await expect(apply(2)).not.toHaveAttribute("aria-disabled", "true");
            await userEvent.click(canvas.getByRole("button", { name: "None" }));
            await expect(canvas.getByRole("checkbox", { name: "# Intro" })).not.toBeChecked();
            await expect(canvas.getByRole("checkbox", { name: "# Results" })).not.toBeChecked();
            await expect(summary()).toHaveTextContent(exactly("2 sections changed"));
            await expect(apply(0)).toHaveAttribute("aria-disabled", "true");
        });
    },
};
