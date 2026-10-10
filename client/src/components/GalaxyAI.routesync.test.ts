import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
    ChatInputStub,
    chatReply,
    deferredResponse,
    messageTexts,
    mockGet,
    mockPost,
    mountChat,
    sendMessage,
} from "./GalaxyAI/test-utils";

const { routeMock, routerMock } = vi.hoisted(() => ({
    routeMock: { path: "/galaxyai", params: {}, query: {} as Record<string, string> },
    routerMock: { push: vi.fn(), replace: vi.fn() },
}));

// Center (route) mode: the component keeps the /galaxyai/<exchange> path in sync.
vi.mock("vue-router", () => ({
    useRoute: () => routeMock,
    useRouter: () => routerMock,
}));

describe("GalaxyAI route sync", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockGet.mockResolvedValue({ data: [], error: undefined });
        routeMock.path = "/galaxyai";
        routeMock.query = {};
    });

    async function mountFreshChat() {
        const mounted = await mountChat();
        // the fresh conversation the component starts with already synced the route
        routerMock.replace.mockClear();
        return mounted;
    }

    it("routes to the saved exchange once its history load finishes", async () => {
        mockPost.mockResolvedValue(chatReply("Here you go", "exchange-123"));
        const { wrapper } = await mountFreshChat();

        await sendMessage(wrapper, "find me a mapper");

        expect(routerMock.replace).toHaveBeenCalledWith("/galaxyai/exchange-123");
    });

    it("prefills a question seeded through the route and drops the parameter", async () => {
        routeMock.path = "/galaxyai/new";
        routeMock.query = { compact: "true", q: "trim my reads" };
        const { wrapper } = await mountChat({ compact: true, exchangeId: "new", initialQuestion: "trim my reads" });

        expect(wrapper.findComponent(ChatInputStub).props("value")).toBe("trim my reads");
        // the seeded question is only prefilled, never sent on the user's behalf
        expect(mockPost).not.toHaveBeenCalled();
        // only `?q=` is dropped, in place, so a reload starts empty
        expect(routerMock.replace).toHaveBeenCalledTimes(1);
        expect(routerMock.replace).toHaveBeenCalledWith({ path: "/galaxyai/new", query: { compact: "true" } });

        // the navigation clears the prop but leaves the prefilled question in place
        await wrapper.setProps({ initialQuestion: undefined });
        await flushPromises();
        expect(wrapper.findComponent(ChatInputStub).props("value")).toBe("trim my reads");
    });

    it("does not route back to the previous exchange when a new chat is started", async () => {
        mockPost.mockResolvedValue(chatReply("Here you go", "exchange-123"));
        const { wrapper, chatStore } = await mountFreshChat();

        // the history refresh triggered by the new exchange id — left in flight
        const historyLoad = deferredResponse<{ data: never[]; error: undefined }>();
        mockGet.mockReturnValueOnce(historyLoad.promise);

        await sendMessage(wrapper, "find me a mapper");
        // the route can only be updated once that refresh settles
        expect(routerMock.replace).not.toHaveBeenCalled();

        chatStore.requestNewChat();
        await flushPromises();
        expect(routerMock.replace).toHaveBeenCalledWith("/galaxyai/new");
        expect(messageTexts(wrapper)).toHaveLength(1);

        historyLoad.resolve({ data: [], error: undefined });
        await flushPromises();

        expect(routerMock.replace).not.toHaveBeenCalledWith("/galaxyai/exchange-123");
        const texts = messageTexts(wrapper);
        expect(texts).toHaveLength(1);
        expect(texts[0]).toContain("New conversation started");
    });
});
