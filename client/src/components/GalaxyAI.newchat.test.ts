import type { VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
    chatReply,
    deferredResponse,
    messageTexts,
    mockGet,
    mockPost,
    mountChat,
    sendMessage,
} from "./GalaxyAI/test-utils";

vi.mock("vue-router", () => ({
    useRoute: () => ({ path: "/", params: {}, query: {} }),
    useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

const NEW_CONVERSATION = expect.stringContaining("New conversation started");

function chatFailure(status: number, error: unknown) {
    return { data: undefined, error, response: { status } };
}

function isAwaitingReply(wrapper: VueWrapper) {
    return wrapper.find(".loading-entry").exists();
}

describe("GalaxyAI", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockGet.mockResolvedValue({ data: [], error: undefined });
    });

    it("appends the response and records the exchange id on a normal exchange", async () => {
        mockPost.mockResolvedValue(chatReply("Here you go", "exchange-123"));
        const { wrapper, chatStore } = await mountChat();

        await sendMessage(wrapper, "find me a mapper");

        expect(messageTexts(wrapper)).toEqual([NEW_CONVERSATION, "find me a mapper", "Here you go"]);
        expect(chatStore.activeChatId).toBe("exchange-123");
    });

    it("resets an unsaved conversation when a new chat is requested mid-flight", async () => {
        const reply = deferredResponse<ReturnType<typeof chatReply>>();
        mockPost.mockReturnValue(reply.promise);
        const { wrapper, chatStore } = await mountChat();

        await sendMessage(wrapper, "what mappers are available?");
        expect(messageTexts(wrapper)).toEqual([NEW_CONVERSATION, "what mappers are available?"]);
        expect(isAwaitingReply(wrapper)).toBe(true);
        // the conversation is unsaved — no exchange id yet, so the identity
        // (activeChatId) would not change and a plain showChat(null) is a no-op
        expect(chatStore.activeChatId).toBeNull();

        chatStore.requestNewChat();
        await flushPromises();

        expect(messageTexts(wrapper)).toEqual([NEW_CONVERSATION]);
        expect(isAwaitingReply(wrapper)).toBe(false);

        // the stale response must not be appended or re-attach the old exchange
        reply.resolve(chatReply("Late answer", "exchange-123"));
        await flushPromises();

        expect(messageTexts(wrapper)).toEqual([NEW_CONVERSATION]);
        expect(chatStore.activeChatId).toBeNull();
    });

    it("does not let a stale response clobber a newly started conversation", async () => {
        const firstReply = deferredResponse<ReturnType<typeof chatReply>>();
        const secondReply = deferredResponse<ReturnType<typeof chatReply>>();
        mockPost.mockReturnValueOnce(firstReply.promise).mockReturnValueOnce(secondReply.promise);
        const { wrapper, chatStore } = await mountChat();

        await sendMessage(wrapper, "first question");
        chatStore.requestNewChat();
        await flushPromises();
        await sendMessage(wrapper, "second question");
        expect(isAwaitingReply(wrapper)).toBe(true);

        firstReply.resolve(chatReply("First answer", "exchange-1"));
        await flushPromises();

        expect(messageTexts(wrapper)).toEqual([NEW_CONVERSATION, "second question"]);
        expect(isAwaitingReply(wrapper)).toBe(true);
        expect(chatStore.activeChatId).toBeNull();

        secondReply.resolve(chatReply("Second answer", "exchange-2"));
        await flushPromises();

        expect(messageTexts(wrapper)).toEqual([NEW_CONVERSATION, "second question", "Second answer"]);
        expect(isAwaitingReply(wrapper)).toBe(false);
        expect(chatStore.activeChatId).toBe("exchange-2");
    });

    it("uses its own wording for a gateway failure rather than the normalized one", async () => {
        mockPost.mockResolvedValue(
            chatFailure(504, { err_msg: "Galaxy took too long to respond (504)", err_code: 504 }),
        );
        const { wrapper } = await mountChat();

        await sendMessage(wrapper, "how do I remove the first row of a table?");

        expect(messageTexts(wrapper)).toEqual([
            NEW_CONVERSATION,
            "how do I remove the first row of a table?",
            "Error: GalaxyAI took too long to respond (504). Please try again.",
        ]);
    });

    it("shows the message from a genuine API error", async () => {
        mockPost.mockResolvedValue(
            chatFailure(400, { err_msg: "No agent is configured for that request", err_code: 400 }),
        );
        const { wrapper } = await mountChat();

        await sendMessage(wrapper, "route this somewhere");

        expect(messageTexts(wrapper)).toEqual([
            NEW_CONVERSATION,
            "route this somewhere",
            expect.stringContaining("No agent is configured for that request"),
        ]);
    });

    // The API client normalizes failures into objects, so this only bites if a
    // response reaches the chat without going through it.
    it("never puts an unparsed body in the conversation", async () => {
        mockPost.mockResolvedValue(chatFailure(500, "<h1>500 Internal Server Error</h1><hr><center>nginx</center>"));
        const { wrapper } = await mountChat();

        await sendMessage(wrapper, "anything");

        expect(messageTexts(wrapper)).toEqual([
            NEW_CONVERSATION,
            "anything",
            "Error: GalaxyAI could not answer that request (500). Please try again.",
        ]);
    });
});
