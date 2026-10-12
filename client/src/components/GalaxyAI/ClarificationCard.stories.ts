import type { Meta, StoryObj } from "@storybook/vue3-vite";

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
export const QuickReplyChoices: Story = {};

/** The router needs an answer the viewer can type rather than choose from suggestions. */
export const FreeTextAnswer: Story = {
    args: { options: [] },
};
