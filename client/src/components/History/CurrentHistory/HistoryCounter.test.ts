import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { RegisteredUser } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
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

// userStore wires its localStorage-backed refs through this composable; the
// real watcher hits ``window.localStorage`` which jsdom doesn't expose with a
// usable Storage prototype here. We don't read any of those refs in this
// test, so a ref-returning stub is enough to keep userStore initialization
// happy.
vi.mock("@/composables/userLocalStorageFromHashedId", async () => {
    const { ref } = await import("vue");
    return {
        useUserLocalStorageFromHashId: <T>(_key: string, initialValue: T) => ref(initialValue),
    };
});

const { server, http } = useServerMock();

const localVue = getLocalVue();

const baseHistory = {
    id: "hist-1",
    name: "Test history",
    user_id: "user-1",
    size: 0,
    contents_active: { active: 0, deleted: 0, hidden: 0 },
    update_time: new Date().toISOString(),
    create_time: new Date().toISOString(),
    deleted: false,
    archived: false,
    purged: false,
    published: false,
};

function registerConfigHandler(enableSse: boolean): void {
    server.use(
        http.get("/api/configuration", ({ response }) => {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return response(200).json({ enable_sse_updates: enableSse } as any);
        }),
    );
}

function setEnableSse(enabled: boolean): void {
    registerConfigHandler(enabled);
    // The store kicks off ``loadConfig`` on creation; ``setConfiguration``
    // makes the value visible synchronously regardless of the network round
    // trip so the component reads it on mount.
    useConfigStore().setConfiguration({ enable_sse_updates: enabled } as never);
    // The refresh button is gated on ``currentUser``; without a logged-in
    // user the BButtonGroup that contains it is never rendered.
    useUserStore().currentUser = { id: "user-1", email: "u@example.com" } as RegisteredUser;
}

function mountCounter(props: Partial<{ lastChecked: Date; isWatching: boolean }> = {}) {
    return shallowMount(HistoryCounter as unknown as object, {
        propsData: {
            history: baseHistory,
            lastChecked: props.lastChecked ?? new Date(),
            isWatching: props.isWatching ?? true,
        },
        localVue,
    });
}

function refreshButton(wrapper: ReturnType<typeof shallowMount>) {
    return wrapper.get(".history-refresh-button");
}

describe("HistoryCounter — refresh button", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        sseState.connect.mockClear();
        sseState.disconnect.mockClear();
        // sseMockFactory lazily creates these refs on first call; reset to a
        // known state for each test.
        Reflect.deleteProperty(sseState, "connected");
        Reflect.deleteProperty(sseState, "hasEverConnected");
        // Re-create refs by invoking the factory once — every component mount
        // already triggers this, but doing it explicitly makes the per-test
        // state setup obvious.
        sseMockFactory(sseState);
        vi.useFakeTimers();
    });

    afterEach(() => {
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
            expect(button.attributes("variant")).toBe("link");
        });

        it("does not flag the initial-connect window as a connection loss", async () => {
            // EventSource hasn't opened yet — connected=false, hasEverConnected=false.
            setSseConnected(sseState, false);
            setSseHasEverConnected(sseState, false);

            const wrapper = mountCounter();
            await flushPromises();

            const button = refreshButton(wrapper);
            expect(button.attributes("title")).toBe("Refresh history");
            expect(button.attributes("variant")).toBe("link");
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
            expect(button.attributes("variant")).toBe("danger");
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
            expect(button.attributes("variant")).toBe("link");
        });

        it("turns red after 2 minutes of staleness", async () => {
            // 3 minutes ago — past the 120000ms cutoff in HistoryCounter.
            const stale = new Date(Date.now() - 3 * 60 * 1000);
            const wrapper = mountCounter({ lastChecked: stale, isWatching: true });
            await flushPromises();

            const button = refreshButton(wrapper);
            expect(button.attributes("title")).toMatch(/Consider reloading the page\.$/);
            expect(button.attributes("variant")).toBe("danger");
        });

        it("turns red when the resource watcher reports it is no longer watching", async () => {
            const wrapper = mountCounter({ lastChecked: new Date(), isWatching: false });
            await flushPromises();

            const button = refreshButton(wrapper);
            expect(button.attributes("variant")).toBe("danger");
        });
    });

    it("emits reloadContents when the refresh button is clicked", async () => {
        setEnableSse(true);
        setSseConnected(sseState, true);
        setSseHasEverConnected(sseState, true);

        const wrapper = mountCounter();
        await flushPromises();
        await refreshButton(wrapper).trigger("click");

        expect(wrapper.emitted("reloadContents")).toBeTruthy();
        expect(wrapper.emitted("reloadContents")?.length).toBe(1);
    });
});
