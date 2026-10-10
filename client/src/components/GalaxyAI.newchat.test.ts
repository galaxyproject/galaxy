import { composeStories } from "@storybook/vue3-vite";
import { deferred } from "@tests/vitest/deferred";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import type { VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, type MockInstance, vi } from "vitest";
import { nextTick } from "vue";

import { GalaxyApi } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { useChatStore } from "@/stores/chatStore";

import * as GalaxyAIStories from "./GalaxyAI.stories";
import { chatResponse, MAPPER_ANSWER, NEW_EXCHANGE_ID } from "./GalaxyAI/test_fixtures";

import ChatInput from "./GalaxyAI/ChatInput.vue";

const stories = composeStories(GalaxyAIStories);
const mountStory = useStoryMount();
const { server, http } = useServerMock();

const NEW_CONVERSATION = expect.stringContaining("New conversation started");

let post: MockInstance;

beforeEach(() => {
    // Passes through to the stories' handlers; awaiting its results waits for an answer to arrive.
    post = vi.spyOn(GalaxyApi(), "POST");
});

afterEach(() => {
    post.mockRestore();
});

async function mountChat(story: StoryOf<typeof stories> = stories.NewConversation) {
    const wrapper = mountStory(story);
    await flushPromises();
    return { wrapper, chatStore: useChatStore() };
}

/** The text of every message in the conversation, oldest first. */
function messageTexts(wrapper: VueWrapper) {
    return wrapper.findAll(".system-notice, .query-text, .response-content").map((message) => message.text());
}

/** Type `text` into the chat input, submit it, and let the request start. */
async function sendMessage(wrapper: VueWrapper, text: string) {
    const input = wrapper.findComponent(ChatInput);
    input.vm.$emit("input", text);
    await nextTick();
    input.vm.$emit("submit");
    await flushPromises();
}

/** Waits until the answer to the `index`th question has reached the chat. */
async function answerArrived(index: number) {
    await post.mock.results[index]!.value;
    await flushPromises();
}

/** Holds the next question's answer until the test releases it. */
function holdNextAnswer() {
    const release = deferred<{ response: string; exchangeId: string }>();
    server.use(
        http.post(
            "/api/chat",
            async ({ response }) => {
                const { response: answer, exchangeId } = await release.promise;
                return response(200).json(chatResponse(answer, exchangeId));
            },
            { once: true },
        ),
    );
    return (response: string, exchangeId: string) => release.resolve({ response, exchangeId });
}

function isAwaitingReply(wrapper: VueWrapper) {
    return wrapper.find(".loading-entry").exists();
}

describe("GalaxyAI", () => {
    it("appends the response and records the exchange id on a normal exchange", async () => {
        const { wrapper, chatStore } = await mountChat();

        await sendMessage(wrapper, "find me a mapper");
        await answerArrived(0);

        expect(messageTexts(wrapper)).toEqual([NEW_CONVERSATION, "find me a mapper", MAPPER_ANSWER]);
        expect(chatStore.activeChatId).toBe(NEW_EXCHANGE_ID);
    });

    it("resets an unsaved conversation when a new chat is requested mid-flight", async () => {
        const { wrapper, chatStore } = await mountChat();
        const releaseAnswer = holdNextAnswer();

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
        releaseAnswer("Late answer", "exchange-123");
        await answerArrived(0);

        expect(messageTexts(wrapper)).toEqual([NEW_CONVERSATION]);
        expect(chatStore.activeChatId).toBeNull();
    });

    it("does not let a stale response clobber a newly started conversation", async () => {
        const { wrapper, chatStore } = await mountChat();
        const releaseFirstAnswer = holdNextAnswer();

        await sendMessage(wrapper, "first question");
        chatStore.requestNewChat();
        await flushPromises();
        const releaseSecondAnswer = holdNextAnswer();
        await sendMessage(wrapper, "second question");
        expect(isAwaitingReply(wrapper)).toBe(true);

        releaseFirstAnswer("First answer", "exchange-1");
        await answerArrived(0);

        expect(messageTexts(wrapper)).toEqual([NEW_CONVERSATION, "second question"]);
        expect(isAwaitingReply(wrapper)).toBe(true);
        expect(chatStore.activeChatId).toBeNull();

        releaseSecondAnswer("Second answer", "exchange-2");
        await answerArrived(1);

        expect(messageTexts(wrapper)).toEqual([NEW_CONVERSATION, "second question", "Second answer"]);
        expect(isAwaitingReply(wrapper)).toBe(false);
        expect(chatStore.activeChatId).toBe("exchange-2");
    });

    it("uses its own wording for a gateway failure rather than the normalized one", async () => {
        const { wrapper } = await mountChat(stories.GatewayTimeout);

        await sendMessage(wrapper, "how do I remove the first row of a table?");
        await answerArrived(0);

        expect(messageTexts(wrapper)).toEqual([
            NEW_CONVERSATION,
            "how do I remove the first row of a table?",
            "Error: GalaxyAI took too long to respond (504). Please try again.",
        ]);
    });

    it("shows the message from a genuine API error", async () => {
        const { wrapper } = await mountChat(stories.SessionExpired);

        await sendMessage(wrapper, "route this somewhere");
        await answerArrived(0);

        expect(messageTexts(wrapper)).toEqual([
            NEW_CONVERSATION,
            "route this somewhere",
            "Error: Action requires user authentication.",
        ]);
    });

    // The API client normalizes failures into objects, so no story can produce this; it only
    // bites if a response reaches the chat without going through the client.
    it("never puts an unparsed body in the conversation", async () => {
        post.mockResolvedValueOnce({
            data: undefined,
            error: "<h1>500 Internal Server Error</h1><hr><center>nginx</center>",
            response: { status: 500 },
        });
        const { wrapper } = await mountChat();

        await sendMessage(wrapper, "anything");
        await answerArrived(0);

        expect(messageTexts(wrapper)).toEqual([
            NEW_CONVERSATION,
            "anything",
            "Error: GalaxyAI could not answer that request (500). Please try again.",
        ]);
    });
});
