import { getFakeHistorySummaryExtended, getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount, shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { setSseConnected, setSseHasEverConnected, sseMockFactory } from "@/stores/_testing/sseStoreSupport";
import { useConfigStore } from "@/stores/configurationStore";
import { useUserStore } from "@/stores/userStore";

import HistoryCounter from "./HistoryCounter.vue";

const sseState = vi.hoisted(() => ({
    onEvent: null as ((event: MessageEvent) => void) | null,
    connect: vi.fn(),
    disconnect: vi.fn(),
}));

vi.mock("@/composables/useNotificationSSE", () => sseMockFactory(sseState));

// These storage-backed preferences are unrelated to the refresh button.
vi.mock("@/composables/userLocalStorageFromHashedId", async () => {
    const { ref } = await import("vue");
    return {
        useUserLocalStorageFromHashId: <T>(_key: string, initialValue: T) => ref(initialValue),
    };
});

const { server, http } = useServerMock();

enableAutoUnmount(afterEach);
const now = new Date("2026-01-01T12:00:00Z");

function setEnableSse(enabled: boolean): void {
    server.use(
        http.get("/api/configuration", ({ response }) =>
            response.untyped(HttpResponse.json({ enable_sse_updates: enabled })),
        ),
    );
    // Match the pending response synchronously so mount does not depend on its timing.
    useConfigStore(pinia).setConfiguration({ enable_sse_updates: enabled });
    useUserStore(pinia).currentUser = getFakeRegisteredUser({ id: "user-1", email: "u@example.com" });
}

let pinia: ReturnType<typeof createPinia>;

function mountCounter(props: Partial<{ lastChecked: Date; isWatching: boolean }> = {}, renderButtons = false) {
    const localVue = getLocalVue();
    setActivePinia(pinia);
    const options = {
        props: {
            history: {
                ...getFakeHistorySummaryExtended({
                    id: "hist-1",
                    name: "Test history",
                    user_id: "user-1",
                    size: 0,
                    contents_active: { active: 0, deleted: 0, hidden: 0 },
                    update_time: now.toISOString(),
                }),
                create_time: now.toISOString(),
            },
            lastChecked: props.lastChecked ?? new Date(),
            isWatching: props.isWatching ?? true,
        },
        global: withPlugins(localVue, pinia),
    };
    // Stub for prop assertions; real mount so clicks reach GButton's handler.
    return renderButtons ? mount(HistoryCounter as object, options) : shallowMount(HistoryCounter as object, options);
}

function refreshButton(wrapper: ReturnType<typeof shallowMount>) {
    return wrapper.get(".history-refresh-button");
}

describe("HistoryCounter — refresh button", () => {
    beforeEach(() => {
        pinia = createPinia();
        setActivePinia(pinia);
        sseState.connect.mockClear();
        sseState.disconnect.mockClear();
        setSseConnected(sseState, false);
        setSseHasEverConnected(sseState, false);
        vi.useFakeTimers();
        vi.setSystemTime(now);
    });

    afterEach(() => {
        vi.clearAllTimers();
        vi.useRealTimers();
    });

    describe("SSE mode", () => {
        beforeEach(() => {
            setEnableSse(true);
        });

        it('shows "Refresh history" with a link variant when the connection is healthy', async () => {
            setSseConnected(sseState, true);
            setSseHasEverConnected(sseState, true);

            const wrapper = mountCounter();
            await flushPromises();

            const button = refreshButton(wrapper);
            expect(button.attributes("title")).toBe("Refresh history");
            // ``link`` variant maps to ``transparent`` + ``color=blue`` via variantToColor()
            // to preserve Bootstrap's link-blue text color on the GButton render.
            expect(button.attributes("transparent")).toBe("true");
            expect(button.attributes("color")).toBe("blue");
        });

        it("does not flag the initial-connect window as a connection loss", async () => {
            // EventSource hasn't opened yet — connected=false, hasEverConnected=false.
            setSseConnected(sseState, false);
            setSseHasEverConnected(sseState, false);

            const wrapper = mountCounter();
            await flushPromises();

            const button = refreshButton(wrapper);
            expect(button.attributes("title")).toBe("Refresh history");
            expect(button.attributes("transparent")).toBe("true");
            expect(button.attributes("color")).toBe("blue");
        });

        it("turns red when the SSE connection is lost after a successful open", async () => {
            setSseConnected(sseState, true);
            setSseHasEverConnected(sseState, true);

            const wrapper = mountCounter();
            await flushPromises();

            // Simulate the EventSource onerror path: connection drops after
            // it had previously been established.
            setSseConnected(sseState, false);
            await flushPromises();

            const button = refreshButton(wrapper);
            expect(button.attributes("title")).toBe("Live updates disconnected. Click to refresh.");
            // ``danger`` variant maps to color=red via variantToColor().
            expect(button.attributes("color")).toBe("red");
        });
    });

    describe("polling mode", () => {
        beforeEach(() => {
            setEnableSse(false);
        });

        it("shows the legacy 'Last refreshed …' title with a link variant when fresh", async () => {
            const wrapper = mountCounter({ lastChecked: new Date(), isWatching: true });
            await flushPromises();

            const button = refreshButton(wrapper);
            expect(button.attributes("title")).toMatch(/^Last refreshed .+ ago$/);
            expect(button.attributes("transparent")).toBe("true");
            expect(button.attributes("color")).toBe("blue");
        });

        it("turns red after 2 minutes of staleness", async () => {
            // 3 minutes ago — past the 120000ms cutoff in HistoryCounter.
            const stale = new Date(Date.now() - 3 * 60 * 1000);
            const wrapper = mountCounter({ lastChecked: stale, isWatching: true });
            await flushPromises();

            const button = refreshButton(wrapper);
            expect(button.attributes("title")).toMatch(/Consider reloading the page\.$/);
            expect(button.attributes("color")).toBe("red");
        });

        it("turns red when the resource watcher reports it is no longer watching", async () => {
            const wrapper = mountCounter({ lastChecked: new Date(), isWatching: false });
            await flushPromises();

            const button = refreshButton(wrapper);
            expect(button.attributes("color")).toBe("red");
        });
    });

    it("emits reloadContents when the refresh button is clicked", async () => {
        setEnableSse(true);
        setSseConnected(sseState, true);
        setSseHasEverConnected(sseState, true);

        const wrapper = mountCounter({}, true);
        await flushPromises();

        await refreshButton(wrapper).trigger("click");

        expect(wrapper.emitted("reloadContents")).toEqual([[]]);
    });
});
