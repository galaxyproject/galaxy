import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { http as mswHttp, HttpResponse } from "msw";

import { http } from "@/api/client/__mocks__/http";

import { chatAnswers, MAPPER_ANSWER } from "./GalaxyAI/test_fixtures";

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

/** A fresh conversation; questions get an answer about read mappers. */
export const NewConversation: Story = {};

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
};
