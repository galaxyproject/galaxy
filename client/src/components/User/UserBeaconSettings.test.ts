import { getFakeHistorySummary, getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import type { BeaconHistory } from "@/api/histories";
import type * as HistoryStoreModule from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import UserBeaconSettings from "./UserBeaconSettings.vue";

enableAutoUnmount(afterEach);
const { server, http } = useServerMock();

const TEST_USER_ID = "test_user_id";
const BEACON_HISTORY_ID = "beacon_history_id";

const mockSetCurrentHistory = vi.fn();
const mockUpdateHistory = vi.fn();

vi.mock("@/stores/historyStore", async () => {
    const original = await vi.importActual<typeof HistoryStoreModule>("@/stores/historyStore");
    return {
        ...original,
        useHistoryStore: () => ({
            ...original.useHistoryStore(),
            currentHistoryId: "other_history_id",
            setCurrentHistory: mockSetCurrentHistory,
            updateHistory: mockUpdateHistory,
        }),
    };
});

function setupBeaconHandlers(enabled: boolean, histories: BeaconHistory[] = []) {
    server.use(
        http.get("/api/users/{user_id}/beacon", ({ response }) => response(200).json({ enabled })),
        http.get("/api/histories", ({ response }) => response.untyped(HttpResponse.json(histories))),
    );
}

function beaconHistory(contentsActive: BeaconHistory["contents_active"]): BeaconHistory {
    return {
        id: BEACON_HISTORY_ID,
        create_time: "2024-01-01T00:00:00.000Z",
        contents_active: contentsActive,
    };
}

function getButton(wrapper: VueWrapper, text: string) {
    const button = wrapper.findAll("button").find((candidate) => candidate.text() === text);
    if (!button) {
        throw new Error(`Button '${text}' was not rendered`);
    }
    return button;
}

async function mountComponent() {
    const global = getLocalVue(true);
    const pinia = createPinia();
    setActivePinia(pinia);
    // Set user before mounting so userId is available when onOpenModal() runs in setup
    const userStore = useUserStore();
    userStore.currentUser = getFakeRegisteredUser({ id: TEST_USER_ID });
    const wrapper = mount(UserBeaconSettings, { global: withPlugins(global, pinia) });
    await flushPromises();
    return wrapper;
}

describe("UserBeaconSettings.vue", () => {
    beforeEach(() => {
        vi.resetAllMocks();
    });

    it("shows disabled state on load when beacon is off", async () => {
        setupBeaconHandlers(false);
        const wrapper = await mountComponent();

        expect(wrapper.text()).toContain("disabled");
        expect(wrapper.text()).toContain("Enable");
        expect(wrapper.text()).not.toContain("Disable");
    });

    it("shows enabled state when beacon is on", async () => {
        setupBeaconHandlers(true, [beaconHistory({ active: 3, hidden: 0, deleted: 0 })]);
        const wrapper = await mountComponent();

        expect(wrapper.text()).toContain("enabled");
        expect(wrapper.text()).toContain("Disable");
        expect(wrapper.text()).not.toContain("no data will be shared");
    });

    it("shows 'No beacon history found' and Create button when enabled but no histories", async () => {
        setupBeaconHandlers(true, []);
        const wrapper = await mountComponent();

        expect(wrapper.text()).toContain("No beacon history found");
        expect(wrapper.text()).toContain("Create Beacon History");
    });

    it("shows history table with correct active dataset count", async () => {
        setupBeaconHandlers(true, [beaconHistory({ active: 7, hidden: 2, deleted: 1 })]);
        const wrapper = await mountComponent();

        expect(wrapper.text()).toContain("Beacon Export");
        expect(wrapper.text()).toContain("7 datasets");
        expect(wrapper.text()).not.toContain("9 datasets");
    });

    it("enables beacon when Enable button is clicked", async () => {
        setupBeaconHandlers(false);
        server.use(http.post("/api/users/{user_id}/beacon", ({ response }) => response(200).json({ enabled: true })));
        const wrapper = await mountComponent();

        await getButton(wrapper, "Enable").trigger("click");
        await flushPromises();

        expect(wrapper.text()).toContain("enabled");
    });

    it("disables beacon when Disable button is clicked", async () => {
        setupBeaconHandlers(true, [beaconHistory({ active: 2, hidden: 0, deleted: 0 })]);
        server.use(http.post("/api/users/{user_id}/beacon", ({ response }) => response(200).json({ enabled: false })));
        const wrapper = await mountComponent();

        await getButton(wrapper, "Disable").trigger("click");
        await flushPromises();

        expect(wrapper.text()).toContain("disabled");
    });

    it("creates beacon history when Create button is clicked", async () => {
        setupBeaconHandlers(true, []);
        const wrapper = await mountComponent();

        expect(wrapper.text()).toContain("No beacon history found");

        // Add handlers for the create + re-fetch after mountComponent so initial GET returns []
        server.use(
            http.post("/api/histories", ({ response }) =>
                response(200).json(getFakeHistorySummary({ id: BEACON_HISTORY_ID, name: "Beacon Export 📡" })),
            ),
            http.get("/api/histories", ({ response }) =>
                response.untyped(HttpResponse.json([beaconHistory({ active: 0, hidden: 0, deleted: 0 })])),
            ),
        );

        await getButton(wrapper, "Create Beacon History").trigger("click");
        await flushPromises();

        expect(mockUpdateHistory).toHaveBeenCalledWith(
            BEACON_HISTORY_ID,
            expect.objectContaining({ annotation: expect.any(String) }),
        );
        expect(wrapper.text()).toContain("Beacon Export");
    });

    it("calls setCurrentHistory when Switch to History is clicked", async () => {
        setupBeaconHandlers(true, [beaconHistory({ active: 1, hidden: 0, deleted: 0 })]);
        const wrapper = await mountComponent();

        await getButton(wrapper, "Switch to History").trigger("click");
        await flushPromises();

        expect(mockSetCurrentHistory).toHaveBeenCalledWith(BEACON_HISTORY_ID);
    });
});
