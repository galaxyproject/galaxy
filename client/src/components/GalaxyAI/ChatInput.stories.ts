import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { withModel } from "@tests/test-data/withModel";
import { fn } from "storybook/test";
import { h } from "vue";

import ChatInput from "./ChatInput.vue";

// Forward submission listeners through attrs while the model parent owns input changes.
export const ChatInputWithModel = Object.assign(withModel(ChatInput, "ChatInputWithModel"), {
    compatConfig: { MODE: 3 as const },
});
type Args = InstanceType<typeof ChatInput>["$props"];

const meta = {
    title: "GalaxyAI/ChatInput",
    component: ChatInput,
    excludeStories: ["ChatInputWithModel"],
    decorators: [withCurrentUser()],
    render: (args) => () => h(ChatInputWithModel, args),
    args: { value: "", busy: false, onSubmit: fn() },
} satisfies Meta<Args>;

export default meta;
type Story = StoryObj<Args>;

/** Compose a question; typing round-trips through the model parent. */
export const EmptyQuestion: Story = {};

/** A question is ready to submit; submission appears in the Actions panel. */
export const QuestionDraft: Story = { args: { value: "Which tools can align paired-end reads?" } };

/** The conversation is busy answering and temporarily locks the composer. */
export const WaitingForAnswer: Story = {
    args: { value: "Which tools can align paired-end reads?", busy: true },
};

/** The surrounding conversation has disabled question entry. */
export const ConversationUnavailable: Story = { args: { disabled: true } };

/** A longer question expands the composer while retaining its line breaks. */
export const MultilineQuestion: Story = {
    args: {
        value: "I have paired-end RNA-seq reads.\nHow should I trim and align them?\nWhich quality checks should I run?",
    },
};
