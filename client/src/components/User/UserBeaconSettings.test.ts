import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { HistorySummary } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import type { BeaconHistory } from "@/api/histories";
import { useUserStore } from "@/stores/userStore";

import UserBeaconSettings from "./UserBeaconSettings.vue";

const localVue = getLocalVue(true);
const { server, http } = useServerMock();

const TEST_USER_ID = "test_user_id";
const BEACON_HISTORY_ID = "beacon_history_id";

const mockSetCurrentHistory = vi.fn();
const mockUpdateHistory = vi.fn();

vi.mock("@/stores/historyStore", async () => {
    const original = await vi.importActual("@/stores/historyStore");
    return {
        ...original,
        useHistoryStore: () => ({
            ...(original as any).useHistoryStore(),
            currentHistoryId: "other_history_id",
            setCurrentHistory: mockSetCurrentHistory,
            updateHistory: mockUpdateHistory,
        }),
    };
});

function setupBeaconHandlers(enabled: boolean, histories: BeaconHistory[] = []) {
    server.use(
        http.get("/api/users/{user_id}/beacon", ({ response }) => response(200).json({ enabled })),
        http.get("/api/histories", ({ response }) => response(200).json(histories as unknown as HistorySummary[])),
    );
}

async function mountComponent() {
    const pinia = createPinia();
    setActivePinia(pinia);
    // Set user before mounting so userId is available when onOpenModal() runs in setup
    const userStore = useUserStore();
    userStore.currentUser = getFakeRegisteredUser({ id: TEST_USER_ID });
    const wrapper = mount(UserBeaconSettings as object, { localVue, pinia });
    await flushPromises();
    return wrapper;
}

describe("UserBeaconSettings.vue", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("shows disabled state on load when beacon is off", async () => {
        setupBeaconHandlers(false);
        const wrapper = await mountComponent();

        expect(wrapper.text()).toContain("disabled");
        expect(wrapper.text()).toContain("Enable");
        expect(wrapper.text()).not.toContain("Disable");
    });

    it("shows enabled state when beacon is on", async () => {
        setupBeaconHandlers(true, [
            {
                id: BEACON_HISTORY_ID,
                create_time: "2024-01-01T00:00:00.000Z",
                contents_active: { active: 3, hidden: 0, deleted: 0 },
            },
        ]);
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
        setupBeaconHandlers(true, [
            {
                id: BEACON_HISTORY_ID,
                create_time: "2024-01-01T00:00:00.000Z",
                contents_active: { active: 7, hidden: 2, deleted: 1 },
            },
        ]);
        const wrapper = await mountComponent();

        expect(wrapper.text()).toContain("Beacon Export");
        expect(wrapper.text()).toContain("7 datasets");
        expect(wrapper.text()).not.toContain("9 datasets");
    });

    it("enables beacon when Enable button is clicked", async () => {
        setupBeaconHandlers(false);
        server.use(http.post("/api/users/{user_id}/beacon", ({ response }) => response(200).json({ enabled: true })));
        const wrapper = await mountComponent();

        await wrapper.find("button.g-green").trigger("click");
        await flushPromises();

        expect(wrapper.text()).toContain("enabled");
    });

    it("disables beacon when Disable button is clicked", async () => {
        setupBeaconHandlers(true, [
            {
                id: BEACON_HISTORY_ID,
                create_time: "2024-01-01T00:00:00.000Z",
                contents_active: { active: 2, hidden: 0, deleted: 0 },
            },
        ]);
        server.use(http.post("/api/users/{user_id}/beacon", ({ response }) => response(200).json({ enabled: false })));
        const wrapper = await mountComponent();

        await wrapper.find("button.g-red").trigger("click");
        await flushPromises();

        expect(wrapper.text()).toContain("disabled");
    });

    it("creates beacon history when Create button is clicked", async () => {
        setupBeaconHandlers(true, []);
        const wrapper = await mountComponent();

        // Verify "No beacon history found" is shown and the Create button is there
        expect(wrapper.text()).toContain("No beacon history found");

        // Add handlers for the create + re-fetch after mountComponent so initial GET returns []
        server.use(
            http.post("/api/histories", ({ response }) =>
                response(200).json({ id: BEACON_HISTORY_ID, name: "Beacon Export 📡" } as HistorySummary),
            ),
            http.get("/api/histories", ({ response }) =>
                response(200).json([
                    {
                        id: BEACON_HISTORY_ID,
                        create_time: "2024-01-01T00:00:00.000Z",
                        contents_active: { active: 0, hidden: 0, deleted: 0 },
                    } as unknown as HistorySummary,
                ]),
            ),
        );

        // Only one blue button visible when no histories: "Create Beacon History"
        await wrapper.find("button.g-blue").trigger("click");
        await flushPromises();

        expect(mockUpdateHistory).toHaveBeenCalledWith(
            BEACON_HISTORY_ID,
            expect.objectContaining({ annotation: expect.any(String) }),
        );
        expect(wrapper.text()).toContain("Beacon Export");
    });

    it("calls setCurrentHistory when Switch to History is clicked", async () => {
        setupBeaconHandlers(true, [
            {
                id: BEACON_HISTORY_ID,
                create_time: "2024-01-01T00:00:00.000Z",
                contents_active: { active: 1, hidden: 0, deleted: 0 },
            },
        ]);
        const wrapper = await mountComponent();

        await wrapper.find("button.g-blue").trigger("click");
        await flushPromises();

        expect(mockSetCurrentHistory).toHaveBeenCalledWith(BEACON_HISTORY_ID);
    });
});
