import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import { useChatStore } from "@/stores/chatStore";

import type { ChatHistoryItem } from "./chatTypes";

import ChatModeSelector from "./ChatModeSelector.vue";
import GButton from "@/components/BaseComponents/GButton.vue";

const mockPush = vi.fn();
let mockRoute: { path: string; params: Record<string, string>; query: Record<string, string> } = {
    path: "/",
    params: {},
    query: {},
};

vi.mock("vue-router/composables", () => ({
    useRouter: () => ({ push: mockPush }),
    useRoute: () => mockRoute,
}));

const localVue = getLocalVue();

function mountComponent() {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);
    const wrapper = mount(ChatModeSelector as object, {
        localVue,
        pinia,
        stubs: { FontAwesomeIcon: true },
    });
    const store = useChatStore();
    return { wrapper, store };
}

/** Returns the three GButton wrappers in template order: [fullView, sidePanel, bottomPanel] */
function getButtons(wrapper: Wrapper<Vue>) {
    return wrapper.findAllComponents(GButton);
}

describe("ChatModeSelector", () => {
    beforeEach(() => {
        mockRoute = { path: "/", params: {}, query: {} };
        vi.clearAllMocks();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    // ── button active states ───────────────────────────────────────────────────

    describe("button active states", () => {
        it("full view button is pressed when in center mode on /galaxyai route", async () => {
            mockRoute = { path: "/galaxyai/chat-1", params: { exchangeId: "chat-1" }, query: {} };
            const { wrapper, store } = mountComponent();
            store.chatLocation = "center";
            await nextTick();
            expect(getButtons(wrapper).at(0).props("pressed")).toBe(true);
        });

        it("full view button is not pressed when not on galaxyai route", async () => {
            const { wrapper, store } = mountComponent();
            store.chatLocation = "center";
            await nextTick();
            expect(getButtons(wrapper).at(0).props("pressed")).toBe(false);
        });

        it("side panel button is pressed when right panel is open", async () => {
            const { wrapper, store } = mountComponent();
            store.chatLocation = "right";
            store.chatVisible = true;
            await nextTick();
            expect(getButtons(wrapper).at(1).props("pressed")).toBe(true);
        });

        it("side panel button is not pressed when right panel is closed", async () => {
            const { wrapper, store } = mountComponent();
            store.chatLocation = "right";
            store.chatVisible = false;
            await nextTick();
            expect(getButtons(wrapper).at(1).props("pressed")).toBe(false);
        });

        it("bottom panel button is pressed when bottom panel is open", async () => {
            const { wrapper, store } = mountComponent();
            store.chatLocation = "bottom";
            store.chatVisible = true;
            await nextTick();
            expect(getButtons(wrapper).at(2).props("pressed")).toBe(true);
        });

        it("bottom panel button is not pressed when bottom panel is closed", async () => {
            const { wrapper, store } = mountComponent();
            store.chatLocation = "bottom";
            store.chatVisible = false;
            await nextTick();
            expect(getButtons(wrapper).at(2).props("pressed")).toBe(false);
        });
    });

    // ── notebook context ──────────────────────────────────────────────────────

    describe("notebook context", () => {
        it("hides full view button when in notebook context", async () => {
            mockRoute = {
                path: "/histories/hist-1/pages/page-1",
                params: { historyId: "hist-1", pageId: "page-1" },
                query: {},
            };
            const { wrapper } = mountComponent();
            await nextTick();
            // Only 2 buttons should be rendered (side panel + bottom panel)
            expect(getButtons(wrapper).length).toBe(2);
        });

        it("shows full view button when not in notebook context", async () => {
            const { wrapper } = mountComponent();
            await nextTick();
            expect(getButtons(wrapper).length).toBe(3);
        });
    });

    // ── openCenterChat ─────────────────────────────────────────────────────────

    describe("openCenterChat", () => {
        it("calls setLocation('center')", async () => {
            const { wrapper, store } = mountComponent();
            await getButtons(wrapper).at(0).trigger("click");
            expect(store.setLocation).toHaveBeenCalledWith("center");
        });

        it("calls hideChat", async () => {
            const { wrapper, store } = mountComponent();
            await getButtons(wrapper).at(0).trigger("click");
            expect(store.hideChat).toHaveBeenCalled();
        });

        it("routes to /galaxyai/{id} when activeChatId is set", async () => {
            const { wrapper, store } = mountComponent();
            store.activeChatId = "chat-42";
            await getButtons(wrapper).at(0).trigger("click");
            expect(mockPush).toHaveBeenCalledWith("/galaxyai/chat-42");
        });

        it("routes to /galaxyai when activeChatId is null", async () => {
            const { wrapper, store } = mountComponent();
            store.activeChatId = null;
            await getButtons(wrapper).at(0).trigger("click");
            expect(mockPush).toHaveBeenCalledWith("/galaxyai");
        });
    });

    // ── openDockedChat – navigation ────────────────────────────────────────────

    describe("openDockedChat — navigation", () => {
        it("pushes '/' when on /galaxyai root route", async () => {
            mockRoute = { path: "/galaxyai", params: {}, query: {} };
            const { wrapper } = mountComponent();
            await getButtons(wrapper).at(1).trigger("click");
            expect(mockPush).toHaveBeenCalledWith("/");
        });

        it("pushes '/' when on /galaxyai/:id route", async () => {
            mockRoute = { path: "/galaxyai/chat-1", params: { exchangeId: "chat-1" }, query: {} };
            const { wrapper } = mountComponent();
            await getButtons(wrapper).at(1).trigger("click");
            expect(mockPush).toHaveBeenCalledWith("/");
        });

        it("does not navigate when on an unrelated route", async () => {
            mockRoute = { path: "/histories", params: {}, query: {} };
            const { wrapper } = mountComponent();
            await getButtons(wrapper).at(1).trigger("click");
            expect(mockPush).not.toHaveBeenCalled();
        });
    });

    // ── openDockedChat – location ──────────────────────────────────────────────

    describe("openDockedChat — dockChat call", () => {
        it("calls dockChat with 'right' for side panel button", async () => {
            const { wrapper, store } = mountComponent();
            store.activeChatId = "active-chat";
            await getButtons(wrapper).at(1).trigger("click");
            expect(store.dockChat).toHaveBeenCalledWith("right", "active-chat");
        });

        it("calls dockChat with 'bottom' for bottom panel button", async () => {
            const { wrapper, store } = mountComponent();
            store.activeChatId = "active-chat";
            await getButtons(wrapper).at(2).trigger("click");
            expect(store.dockChat).toHaveBeenCalledWith("bottom", "active-chat");
        });

        it("uses routedChatId when coming from center mode with exchangeId in route", async () => {
            mockRoute = { path: "/galaxyai/routed-chat", params: { exchangeId: "routed-chat" }, query: {} };
            const { wrapper, store } = mountComponent();
            store.chatLocation = "center";
            await getButtons(wrapper).at(1).trigger("click");
            expect(store.dockChat).toHaveBeenCalledWith("right", "routed-chat");
        });

        it("uses activeChatId fallback when in center mode but no exchangeId in route", async () => {
            mockRoute = { path: "/galaxyai", params: {}, query: {} };
            const { wrapper, store } = mountComponent();
            store.chatLocation = "center";
            store.activeChatId = "active-chat";
            await getButtons(wrapper).at(1).trigger("click");
            expect(store.dockChat).toHaveBeenCalledWith("right", "active-chat");
        });

        it("uses activeChatId when not in center mode", async () => {
            const { wrapper, store } = mountComponent();
            store.chatLocation = "right";
            store.activeChatId = "active-chat";
            await getButtons(wrapper).at(1).trigger("click");
            expect(store.dockChat).toHaveBeenCalledWith("right", "active-chat");
        });

        it("uses first history item when activeChatId is null but history exists", async () => {
            const { wrapper, store } = mountComponent();
            store.activeChatId = null;
            store.chatHistory = [{ id: "hist-1" } as ChatHistoryItem, { id: "hist-2" } as ChatHistoryItem];
            await getButtons(wrapper).at(1).trigger("click");
            expect(store.dockChat).toHaveBeenCalledWith("right", "hist-1");
        });

        it("uses null when no activeChatId and empty history", async () => {
            const { wrapper, store } = mountComponent();
            store.activeChatId = null;
            store.chatHistory = [];
            await getButtons(wrapper).at(1).trigger("click");
            expect(store.dockChat).toHaveBeenCalledWith("right", null);
        });

        it("prefers activeChatId over first history item when both present", async () => {
            const { wrapper, store } = mountComponent();
            store.activeChatId = "active-chat";
            store.chatHistory = [{ id: "hist-1" } as ChatHistoryItem];
            await getButtons(wrapper).at(1).trigger("click");
            expect(store.dockChat).toHaveBeenCalledWith("right", "active-chat");
        });

        it("does NOT use routedChatId when not in center mode even with exchangeId in route", async () => {
            mockRoute = { path: "/galaxyai/some-chat", params: { exchangeId: "some-chat" }, query: {} };
            const { wrapper, store } = mountComponent();
            store.chatLocation = "right";
            store.activeChatId = "active-chat";
            await getButtons(wrapper).at(1).trigger("click");
            expect(store.dockChat).toHaveBeenCalledWith("right", "active-chat");
            expect(store.dockChat).not.toHaveBeenCalledWith("right", "some-chat");
        });
    });
});
