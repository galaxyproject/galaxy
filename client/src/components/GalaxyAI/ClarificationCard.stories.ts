import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { exactly } from "@tests/test-data/text";
import { expect } from "storybook/test";

import { CLARIFICATION_OPTIONS, CLARIFICATION_QUESTION } from "./test_fixtures";

import ClarificationCard from "./ClarificationCard.vue";

const meta = {
    title: "GalaxyAI/ClarificationCard",
    component: ClarificationCard,
    args: {
        question: CLARIFICATION_QUESTION,
        options: [...CLARIFICATION_OPTIONS],
    },
} satisfies Meta<typeof ClarificationCard>;
export default meta;
type Story = StoryObj<typeof meta>;

/** The router offers quick replies when a request could mean several kinds of help. */
export const QuickReplyChoices: Story = {
    play: async ({ canvas, step }) => {
        await step("Read the clarification question", async () => {
            await expect(canvas.getByText(CLARIFICATION_QUESTION, { exact: true })).toBeVisible();
        });
        await step("Read both quick replies in their offered order", async () => {
            const choices = canvas.getAllByRole("button");
            await expect(choices).toHaveLength(2);
            await expect(choices[0]).toHaveTextContent(exactly("Tool recommendation"));
            await expect(choices[0]).toBeVisible();
            await expect(choices[1]).toHaveTextContent(exactly("Tutorial"));
            await expect(choices[1]).toBeVisible();
        });
    },
};

/** The router needs an answer the viewer can type rather than choose from suggestions. */
export const FreeTextAnswer: Story = {
    args: { options: [] },
    play: async ({ canvas, step }) => {
        await step("Read the question without quick-reply buttons", async () => {
            await expect(canvas.getByText(CLARIFICATION_QUESTION, { exact: true })).toBeVisible();
            await expect(canvas.queryAllByRole("button")).toHaveLength(0);
        });
    },
};
