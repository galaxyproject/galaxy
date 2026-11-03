import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { exactly } from "@tests/test-data/text";
import { http as mswHttp, HttpResponse } from "msw";
import { expect, waitFor } from "storybook/test";

import { http } from "@/api/client/__mocks__/http";

import { chatAnswers, chatResponse, MAPPER_ANSWER, NEW_EXCHANGE_ID } from "./GalaxyAI/test_fixtures";

import GalaxyAI from "./GalaxyAI.vue";

/**
 * The GalaxyAI chat as a side panel, starting a new conversation. No user is signed in, so the
 * panel keeps its conversation in memory rather than in the user's browser storage, and each
 * story starts fresh.
 */
const meta = {
    // Not "GalaxyAI": the chat's parts in GalaxyAI/ get stories under that group.
    title: "GalaxyAI/GalaxyAI",
    component: GalaxyAI,
    args: { panel: true },
    parameters: {
        msw: {
            handlers: {
                chat: chatAnswers(MAPPER_ANSWER),
                // Refreshed once a conversation is saved; the panel doesn't show it.
                chatHistory: http.get("/api/chat/history", ({ response }) => response(200).json([])),
            },
        },
    },
} satisfies Meta<typeof GalaxyAI>;

export default meta;
type Story = StoryObj<typeof meta>;

type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

const NEW_CONVERSATION = "New conversation started. How can I help?";

/** Sees the fresh conversation's notice and the empty message box, and returns the box. */
async function seeNewConversation({ canvas, step }: PlayContext) {
    let input!: HTMLElement;
    await step("See a new conversation and an empty message box", async () => {
        const notice = await canvas.findByText(exactly(NEW_CONVERSATION));
        // Messages fade in.
        await waitFor(() => expect(notice).toBeVisible());
        input = canvas.getByRole("textbox", { name: "Chat message" });
        await expect(input).toHaveValue("");
        await expect(input).toBeEnabled();
    });
    return input;
}

/** Types `question` into the message box and sends it with Enter; sees it under the notice. */
async function askQuestion(context: PlayContext, question: string) {
    const input = await seeNewConversation(context);
    await context.step(`Ask "${question}"`, async () => {
        await context.userEvent.type(input, `${question}{Enter}`);
        const asked = await context.canvas.findByText(exactly(question));
        await waitFor(() => expect(asked).toBeVisible());
        await expectInOrder(context.canvas.getByText(exactly(NEW_CONVERSATION)), asked);
    });
    return input;
}

/** Each element comes after the one before it on the page. */
async function expectInOrder(...elements: HTMLElement[]) {
    for (let i = 1; i < elements.length; i++) {
        const position = elements[i - 1]!.compareDocumentPosition(elements[i]!);
        await expect(position & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    }
}

/** Sees `reply` answer `question` and the message box ready for the next question. */
async function seeReply({ canvas, step }: PlayContext, input: HTMLElement, question: string, reply: string) {
    await step("See the reply under the question and the message box ready again", async () => {
        const answer = await canvas.findByText(exactly(reply));
        await waitFor(() => expect(answer).toBeVisible());
        await expectInOrder(canvas.getByText(exactly(question)), answer);
        await waitFor(() => expect(input).toBeEnabled());
        await expect(input).toHaveValue("");
    });
}

/** A fresh conversation; questions get an answer about read mappers. */
export const NewConversation: Story = {
    play: async (context) => {
        await seeNewConversation(context);
    },
};

/** Answers the question held by `answerHeld`; the handler sets it when the question arrives. */
let answerHeldQuestion: (() => void) | undefined;

/** GalaxyAI takes the question but holds its answer until the play calls `answerHeldQuestion`. */
const answerHeld = http.post("/api/chat", async ({ request, response }) => {
    const { exchange_id } = (await request.json()) ?? {};
    await new Promise<void>((resolve) => {
        answerHeldQuestion = resolve;
    });
    return response(200).json(chatResponse(MAPPER_ANSWER, exchange_id ?? NEW_EXCHANGE_ID));
});

/** The question shows at once; the message box waits until GalaxyAI's answer arrives under it. */
export const AnswersQuestion: Story = {
    parameters: { msw: { handlers: { chat: answerHeld } } },
    play: async (context) => {
        // A failed earlier run can leave its resolver behind.
        answerHeldQuestion = undefined;
        const input = await askQuestion(context, "find me a mapper");
        await context.step("See the message box cleared and waiting for the answer", async () => {
            await waitFor(() => expect(answerHeldQuestion).toBeDefined());
            await expect(input).toHaveValue("");
            await expect(input).toBeDisabled();
            await expect(context.canvas.queryByText(exactly(MAPPER_ANSWER))).not.toBeInTheDocument();
        });
        await context.step("GalaxyAI answers", async () => {
            answerHeldQuestion?.();
            answerHeldQuestion = undefined;
        });
        await seeReply(context, input, "find me a mapper", MAPPER_ANSWER);
    },
};

/**
 * The proxy in front of Galaxy gives up waiting for an answer. Plain `msw`, since the typed handlers stamp
 * failures with Galaxy's request id, and a proxy's page carries none.
 */
export const GatewayTimeout: Story = {
    parameters: {
        msw: {
            handlers: {
                chat: mswHttp.post(
                    "/api/chat",
                    () =>
                        new HttpResponse(
                            "<html><body><center><h1>504 Gateway Time-out</h1></center><hr><center>nginx</center></body></html>",
                            {
                                status: 504,
                                headers: { "Content-Type": "text/html" },
                            },
                        ),
                ),
            },
        },
    },
};

/** A question asked behind a timed-out proxy gets GalaxyAI's own wording, not the proxy's page. */
export const ExplainsGatewayTimeout: Story = {
    ...GatewayTimeout,
    play: async (context) => {
        const question = "how do I remove the first row of a table?";
        const input = await askQuestion(context, question);
        await seeReply(context, input, question, "Error: GalaxyAI took too long to respond (504). Please try again.");
    },
};

/** The user's session ended, so Galaxy refuses the question. */
export const SessionExpired: Story = {
    parameters: {
        msw: {
            handlers: {
                chat: http.post("/api/chat", ({ response }) =>
                    response("4XX").json(
                        { err_msg: "Action requires user authentication.", err_code: 403008 },
                        { status: 403 },
                    ),
                ),
            },
        },
    },
};

/** A command-palette question is prefilled for review, rather than sent automatically. */
export const PrefilledCompactConversation: Story = {
    args: { compact: true, exchangeId: "new", initialQuestion: "trim my reads" },
    play: async ({ canvas, step }) => {
        await step("Review the prefilled question before sending it", async () => {
            const notice = await canvas.findByText(exactly(NEW_CONVERSATION), {}, { timeout: 5000 });
            await waitFor(() => expect(notice).toBeVisible());
            const input = canvas.getByRole("textbox", { name: "Chat message" });
            await expect(input).toBeVisible();
            await expect(input).toHaveValue("trim my reads");
            await expect(input).toBeEnabled();
        });
    },
};

/** A refused question shows Galaxy's own message. */
export const ExplainsSessionExpired: Story = {
    ...SessionExpired,
    play: async (context) => {
        const input = await askQuestion(context, "route this somewhere");
        await seeReply(context, input, "route this somewhere", "Error: Action requires user authentication.");
    },
};
