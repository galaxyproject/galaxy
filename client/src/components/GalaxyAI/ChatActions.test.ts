import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useChatStore } from "@/stores/chatStore";

import ChatActions from "./ChatActions.vue";
import GButton from "@/components/BaseComponents/GButton.vue";

const mockPush = vi.fn();
const mockFrameAdd = vi.fn();
let mockRoute: { path: string; params: Record<string, string> } = { path: "/", params: {} };

vi.mock("vue-router/composables", () => ({
    useRouter: () => ({ push: mockPush }),
    useRoute: () => mockRoute,
}));

vi.mock("@/app", () => ({
    getGalaxyInstance: () => ({ frame: { add: mockFrameAdd } }),
}));

vi.mock("@/stores/activityStore.js", () => ({
    useActivityStore: () => ({ toggledSideBar: null, toggleSideBar: vi.fn() }),
}));

const localVue = getLocalVue();

function mountComponent(source: "center" | "docked" | "panel") {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);
    const wrapper = mount(ChatActions as object, {
        localVue,
        pinia,
        propsData: { source },
        stubs: { FontAwesomeIcon: true },
    });
    const store = useChatStore();
    return { wrapper, store };
}

/** Find a GButton by its title prop */
function findButton(wrapper: Wrapper<Vue>, title: string) {
    const all = wrapper.findAllComponents(GButton);
    for (let i = 0; i < all.length; i++) {
        if (all.at(i).props("title") === title) {
            return all.at(i);
        }
    }
    throw new Error(`GButton with title "${title}" not found`);
}

describe("ChatActions", () => {
    beforeEach(() => {
        mockRoute = { path: "/", params: {} };
        vi.clearAllMocks();
    });
    afterEach(() => {
        vi.restoreAllMocks();
    });

    // ── startNew ──────────────────────────────────────────────────────────────

    describe("startNew", () => {
        it("routes to /galaxyai/new in center mode", async () => {
            const { wrapper } = mountComponent("center");
            await findButton(wrapper, "Start New Chat").trigger("click");
            expect(mockPush).toHaveBeenCalledWith("/galaxyai/new");
        });

        it("calls chatStore.showChat(null) in docked mode", async () => {
            const { wrapper, store } = mountComponent("docked");
            await findButton(wrapper, "Start New Chat").trigger("click");
            expect(store.showChat).toHaveBeenCalledWith(null);
            expect(mockPush).not.toHaveBeenCalled();
        });

        it("calls chatStore.showChat(null) in panel mode", async () => {
            const { wrapper, store } = mountComponent("panel");
            await findButton(wrapper, "Start New Chat").trigger("click");
            expect(store.showChat).toHaveBeenCalledWith(null);
            expect(mockPush).not.toHaveBeenCalled();
        });

        it("emits update:collapsed false in all modes", async () => {
            for (const source of ["center", "docked", "panel"] as const) {
                const { wrapper } = mountComponent(source);
                await findButton(wrapper, "Start New Chat").trigger("click");
                expect(wrapper.emitted("update:collapsed")).toEqual([[false]]);
            }
        });
    });

    // ── maximize ──────────────────────────────────────────────────────────────

    describe("maximize", () => {
        it("calls setLocation('center') and hideChat", async () => {
            const { wrapper, store } = mountComponent("docked");
            await findButton(wrapper, "Open in center view").trigger("click");
            expect(store.setLocation).toHaveBeenCalledWith("center");
            expect(store.hideChat).toHaveBeenCalled();
        });

        it("routes to /galaxyai/{id} when activeChatId is set", async () => {
            const { wrapper, store } = mountComponent("docked");
            store.activeChatId = "chat-42";
            await findButton(wrapper, "Open in center view").trigger("click");
            expect(mockPush).toHaveBeenCalledWith("/galaxyai/chat-42");
        });

        it("routes to /galaxyai when activeChatId is null", async () => {
            const { wrapper, store } = mountComponent("docked");
            store.activeChatId = null;
            await findButton(wrapper, "Open in center view").trigger("click");
            expect(mockPush).toHaveBeenCalledWith("/galaxyai");
        });
    });

    // ── popOut ────────────────────────────────────────────────────────────────

    describe("popOut — center", () => {
        it("uses route.params.exchangeId for the window manager url", async () => {
            mockRoute = { path: "/galaxyai/chat-99", params: { exchangeId: "chat-99" } };
            const { wrapper } = mountComponent("center");
            await findButton(wrapper, "Open in floating window").trigger("click");
            expect(mockFrameAdd).toHaveBeenCalledWith(
                expect.objectContaining({ url: "/galaxyai/chat-99?compact=true" }),
            );
        });

        it("falls back to /galaxyai/new when no exchangeId in route", async () => {
            mockRoute = { path: "/galaxyai", params: {} };
            const { wrapper } = mountComponent("center");
            await findButton(wrapper, "Open in floating window").trigger("click");
            expect(mockFrameAdd).toHaveBeenCalledWith(expect.objectContaining({ url: "/galaxyai/new?compact=true" }));
        });

        it("navigates to /galaxyai/new to start a fresh chat in place", async () => {
            const { wrapper } = mountComponent("center");
            await findButton(wrapper, "Open in floating window").trigger("click");
            expect(mockPush).toHaveBeenCalledWith("/galaxyai/new");
        });
    });

    describe("popOut — docked", () => {
        it("uses chatStore.activeChatId for the window manager url", async () => {
            const { wrapper, store } = mountComponent("docked");
            store.activeChatId = "chat-55";
            await findButton(wrapper, "Open in floating window").trigger("click");
            expect(mockFrameAdd).toHaveBeenCalledWith(
                expect.objectContaining({ url: "/galaxyai/chat-55?compact=true" }),
            );
        });

        it("clears activeChatId and hides the panel", async () => {
            const { wrapper, store } = mountComponent("docked");
            await findButton(wrapper, "Open in floating window").trigger("click");
            expect(store.setActiveChatId).toHaveBeenCalledWith(null);
            expect(store.hideChat).toHaveBeenCalled();
        });
    });

    describe("popOut — panel", () => {
        it("uses chatStore.activeChatId for the window manager url", async () => {
            const { wrapper, store } = mountComponent("panel");
            store.activeChatId = "chat-77";
            await findButton(wrapper, "Open in floating window").trigger("click");
            expect(mockFrameAdd).toHaveBeenCalledWith(
                expect.objectContaining({ url: "/galaxyai/chat-77?compact=true" }),
            );
        });

        it("only hides the panel — does not clear activeChatId", async () => {
            const { wrapper, store } = mountComponent("panel");
            await findButton(wrapper, "Open in floating window").trigger("click");
            expect(store.hideChat).toHaveBeenCalled();
            expect(store.setActiveChatId).not.toHaveBeenCalled();
        });
    });

    // ── dock-to emission ──────────────────────────────────────────────────────

    describe("dock-to emission (center source only)", () => {
        it("emits dock-to with 'right' for the side panel button", async () => {
            const { wrapper } = mountComponent("center");
            await findButton(wrapper, "Dock to side panel").trigger("click");
            expect(wrapper.emitted("dock-to")).toEqual([["right"]]);
        });

        it("emits dock-to with 'bottom' for the bottom panel button", async () => {
            const { wrapper } = mountComponent("center");
            await findButton(wrapper, "Dock to bottom panel").trigger("click");
            expect(wrapper.emitted("dock-to")).toEqual([["bottom"]]);
        });
    });

    // ── close ─────────────────────────────────────────────────────────────────

    describe("close button (non-center sources)", () => {
        it("calls chatStore.hideChat in docked mode", async () => {
            const { wrapper, store } = mountComponent("docked");
            await findButton(wrapper, "Close panel").trigger("click");
            expect(store.hideChat).toHaveBeenCalled();
        });

        it("calls chatStore.hideChat in panel mode", async () => {
            const { wrapper, store } = mountComponent("panel");
            await findButton(wrapper, "Close panel").trigger("click");
            expect(store.hideChat).toHaveBeenCalled();
        });
    });
});
