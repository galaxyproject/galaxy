import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { withModel } from "@tests/test-data/withModel";
import { expect, fn, waitFor } from "storybook/test";
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
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

function sendButton({ canvas }: PlayContext) {
    // The icon-only send control currently has no accessible name; this also works once it gains one.
    return canvas.getByRole("button");
}

async function readComposer(context: PlayContext, value: string, inputDisabled: boolean, sendDisabled: boolean) {
    const input = context.canvas.getByRole("textbox", { name: "Chat message" });
    await expect(input).toBeVisible();
    await expect(input).toHaveValue(value);
    if (inputDisabled) {
        await expect(input).toBeDisabled();
    } else {
        await expect(input).toBeEnabled();
    }
    const send = sendButton(context);
    await expect(send).toBeVisible();
    if (sendDisabled) {
        await expect(send).toHaveAttribute("aria-disabled", "true");
    } else {
        await expect(send).not.toHaveAttribute("aria-disabled");
    }
}

/** Compose a question; typing round-trips through the model parent. */
export const EmptyQuestion: Story = {
    play: async (context) => {
        await context.step("Read an empty composer with the default hint and Send unavailable", async () => {
            await readComposer(context, "", false, true);
            await expect(context.canvas.getByRole("textbox", { name: "Chat message" })).toHaveAttribute(
                "placeholder",
                "Ask about tools, workflows, errors, or anything Galaxy...",
            );
        });
    },
};

/** A question is ready to submit; submission appears in the Actions panel. */
export const QuestionDraft: Story = {
    args: { value: "Which tools can align paired-end reads?" },
    play: async (context) => {
        await context.step("Read a drafted question ready to send", async () => {
            await readComposer(context, "Which tools can align paired-end reads?", false, false);
        });
    },
};

/** The conversation is busy answering and temporarily locks the composer. */
export const WaitingForAnswer: Story = {
    play: async (context) => {
        await context.step("Read the locked composer while an answer is pending", async () => {
            await readComposer(context, "Which tools can align paired-end reads?", true, true);
        });
    },
    args: { value: "Which tools can align paired-end reads?", busy: true },
};

/** The surrounding conversation has disabled question entry. */
export const ConversationUnavailable: Story = {
    args: { disabled: true },
    play: async (context) => {
        await context.step("Read the unavailable empty composer", async () => {
            await readComposer(context, "", true, true);
        });
    },
};

/** A longer question expands the composer while retaining its line breaks. */
export const MultilineQuestion: Story = {
    play: async (context) => {
        await context.step("Read the complete question with its line breaks", async () => {
            await readComposer(
                context,
                "I have paired-end RNA-seq reads.\nHow should I trim and align them?\nWhich quality checks should I run?",
                false,
                false,
            );
        });
    },
    args: {
        value: "I have paired-end RNA-seq reads.\nHow should I trim and align them?\nWhich quality checks should I run?",
    },
};

/** The original literal draft displays its value and enables sending. */
export const HelloDraft: Story = {
    args: { value: "hello" },
    play: async (context) => {
        await context.step("Read the original hello draft and enabled Send control", async () => {
            await readComposer(context, "hello", false, false);
        });
    },
};

/** Whitespace alone cannot be sent. */
export const WhitespaceDraft: Story = {
    args: { value: "   " },
    play: async (context) => {
        await context.step("Read three spaces with Send unavailable", async () => {
            await readComposer(context, "   ", false, true);
        });
    },
};

/** The original hello draft remains locked while busy. */
export const BusyHelloDraft: Story = {
    args: { value: "hello", busy: true },
    play: async (context) => {
        await context.step("Read the busy hello draft with both controls unavailable", async () => {
            await readComposer(context, "hello", true, true);
        });
    },
};

/** A disabled conversation cannot send the original hello draft. */
export const UnavailableHelloDraft: Story = {
    args: { value: "hello", disabled: true },
    play: async (context) => {
        await context.step("Read the disabled hello draft with both controls unavailable", async () => {
            await readComposer(context, "hello", true, true);
        });
    },
};

/** A surrounding chat supplies the original custom hint. */
export const CustomPlaceholder: Story = {
    args: { placeholder: "Type here..." },
    play: async (context) => {
        await context.step("Read the supplied Type here hint", async () => {
            await readComposer(context, "", false, true);
            await expect(context.canvas.getByRole("textbox", { name: "Chat message" })).toHaveAttribute(
                "placeholder",
                "Type here...",
            );
        });
    },
};

/** Typing changes the model-owned Send state, and clearing or spaces cannot be sent. */
export const TypesAndClearsQuestion: Story = {
    play: async (context) => {
        const input = context.canvas.getByRole("textbox", { name: "Chat message" });
        await context.step("Start with no question and Send unavailable", async () => {
            await readComposer(context, "", false, true);
        });
        await context.step("Type hello and enable sending through the model parent", async () => {
            await context.userEvent.type(input, "hello");
            await waitFor(() => expect(sendButton(context)).not.toHaveAttribute("aria-disabled"));
            await expect(input).toHaveValue("hello");
        });
        await context.step("Clear the question and keep whitespace unavailable", async () => {
            await context.userEvent.clear(input);
            await waitFor(() => expect(sendButton(context)).toHaveAttribute("aria-disabled", "true"));
            await expect(input).toHaveValue("");
            await context.userEvent.type(input, "   ");
            await expect(input).toHaveValue("   ");
            await expect(sendButton(context)).toHaveAttribute("aria-disabled", "true");
        });
    },
};

/** Shift+Enter inserts a newline in the question instead of consuming the key as submission. */
export const AddsQuestionLine: Story = {
    args: { value: "hello" },
    play: async (context) => {
        const input = context.canvas.getByRole("textbox", { name: "Chat message" });
        await context.step("Start with the original hello question", async () => {
            await readComposer(context, "hello", false, false);
        });
        await context.step("Insert a question line with Shift+Enter", async () => {
            await context.userEvent.click(input);
            await context.userEvent.keyboard("{End}{Shift>}{Enter}{/Shift}");
            await context.userEvent.type(input, "Which tools should I use?");
            await expect(input).toHaveValue("hello\nWhich tools should I use?");
            await expect(sendButton(context)).not.toHaveAttribute("aria-disabled");
        });
    },
};
