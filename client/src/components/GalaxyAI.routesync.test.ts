import { createTestingPinia } from "@pinia/testing";
import { composeStories } from "@storybook/vue3-vite";
import { deferred } from "@tests/vitest/deferred";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import { enableAutoUnmount, mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { disposePinia, getActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, type MockInstance, onTestFinished, vi } from "vitest";
import { nextTick } from "vue";

import { GalaxyApi } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { useChatStore } from "@/stores/chatStore";
import { ensureDefined } from "@/utils/assertions";

import * as GalaxyAIStories from "./GalaxyAI.stories";
import { NEW_EXCHANGE_ID } from "./GalaxyAI/test_fixtures";

import GalaxyAI from "./GalaxyAI.vue";
import ChatInput from "./GalaxyAI/ChatInput.vue";

const { routeMock, routerMock } = vi.hoisted(() => ({
    routeMock: { path: "/galaxyai", params: {}, query: {} as Record<string, string> },
    routerMock: { push: vi.fn(), replace: vi.fn() },
}));

// Center (route) mode: the component keeps the /galaxyai/<exchange> path in sync.
vi.mock("vue-router", () => ({
    useRoute: () => routeMock,
    useRouter: () => routerMock,
}));

const stories = composeStories(GalaxyAIStories);
const mountStory = useStoryMount();
const { server, http } = useServerMock();
let post: MockInstance;
let get: MockInstance;

afterEach(() => {
    post.mockRestore();
    get.mockRestore();
});
enableAutoUnmount(afterEach);

async function mountOwnedChat(liveSeededQuestion = false) {
    let wrapper: VueWrapper;
    if (liveSeededQuestion) {
        const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
        // Clearing this prop on the same instance is the contract; composing would remount it.
        wrapper = mount(GalaxyAI, {
            props: { ...GalaxyAIStories.default.args, ...GalaxyAIStories.PrefilledCompactConversation.args },
            global: withPlugins(getLocalVue(), pinia),
        });
    } else {
        wrapper = mountStory(stories.NewConversation);
    }
    const pinia = ensureDefined(getActivePinia());
    onTestFinished(() => disposePinia(pinia));
    await flushPromises();
    return { wrapper, chatStore: useChatStore() };
}

function messageTexts(wrapper: VueWrapper) {
    return wrapper.findAll(".system-notice, .query-text, .response-content").map((message) => message.text());
}

async function sendMessage(wrapper: VueWrapper, text: string) {
    const input = wrapper.getComponent(ChatInput);
    input.vm.$emit("input", text);
    await nextTick();
    input.vm.$emit("submit");
    await flushPromises();
    await post.mock.results[0]!.value;
    await flushPromises();
}

describe("GalaxyAI route sync", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        post = vi.spyOn(GalaxyApi(), "POST");
        get = vi.spyOn(GalaxyApi(), "GET");
        routeMock.path = "/galaxyai";
        routeMock.query = {};
    });

    async function mountFreshChat() {
        const mounted = await mountOwnedChat();
        // the fresh conversation the component starts with already synced the route
        routerMock.replace.mockClear();
        return mounted;
    }

    it("routes to the saved exchange once its history load finishes", async () => {
        const { wrapper } = await mountFreshChat();

        await sendMessage(wrapper, "find me a mapper");

        await vi.waitFor(() => expect(routerMock.replace).toHaveBeenCalledWith(`/galaxyai/${NEW_EXCHANGE_ID}`));
    });

    it("prefills a question seeded through the route and drops the parameter", async () => {
        routeMock.path = "/galaxyai/new";
        routeMock.query = { compact: "true", q: "trim my reads" };
        const { wrapper } = await mountOwnedChat(true);

        expect(wrapper.getComponent(ChatInput).props("value")).toBe("trim my reads");
        // the seeded question is only prefilled, never sent on the user's behalf
        expect(post).not.toHaveBeenCalled();
        // only `?q=` is dropped, in place, so a reload starts empty
        expect(routerMock.replace).toHaveBeenCalledTimes(1);
        expect(routerMock.replace).toHaveBeenCalledWith({ path: "/galaxyai/new", query: { compact: "true" } });

        // the navigation clears the prop but leaves the prefilled question in place
        await wrapper.setProps({ initialQuestion: undefined });
        await flushPromises();
        expect(wrapper.getComponent(ChatInput).props("value")).toBe("trim my reads");
    });

    it("does not route back to the previous exchange when a new chat is started", async () => {
        const { wrapper, chatStore } = await mountFreshChat();

        // the history refresh triggered by the new exchange id — left in flight
        const historyLoad = deferred<void>();
        let historyStarted = false;
        server.use(
            http.get(
                "/api/chat/history",
                async ({ response }) => {
                    historyStarted = true;
                    await historyLoad.promise;
                    return response(200).json([]);
                },
                { once: true },
            ),
        );
        onTestFinished(async () => {
            historyLoad.resolve();
            await flushPromises();
        });

        await sendMessage(wrapper, "find me a mapper");
        await vi.waitFor(() => expect(historyStarted).toBe(true));
        // the route can only be updated once that refresh settles
        expect(routerMock.replace).not.toHaveBeenCalled();

        chatStore.requestNewChat();
        await flushPromises();
        expect(routerMock.replace).toHaveBeenCalledWith("/galaxyai/new");
        expect(messageTexts(wrapper)).toHaveLength(1);

        const pendingHistory = get.mock.results.find((_, index) => get.mock.calls[index]?.[0] === "/api/chat/history");
        historyLoad.resolve();
        await pendingHistory!.value;
        await flushPromises();

        expect(routerMock.replace).not.toHaveBeenCalledWith(`/galaxyai/${NEW_EXCHANGE_ID}`);
        const texts = messageTexts(wrapper);
        expect(texts).toHaveLength(1);
        expect(texts[0]).toContain("New conversation started");
    });
});
