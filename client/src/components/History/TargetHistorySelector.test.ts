import { createTestingPinia } from "@pinia/testing";
import { getFakeHistorySummary } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { HistorySummary } from "@/api";
import { useHistoryStore } from "@/stores/historyStore";

import GAlert from "../BaseComponents/GAlert.vue";
import TargetHistoryLink from "./TargetHistoryLink.vue";
import TargetHistorySelector from "./TargetHistorySelector.vue";

enableAutoUnmount(afterEach);

function mountWithHistory(overrides: Partial<HistorySummary> = {}) {
    const history = getFakeHistorySummary({
        id: "active-history",
        name: "Active History",
        annotation: "",
        update_time: "2024-01-01T00:00:00Z",
        url: "/api/histories/mock-history",
        ...overrides,
    });
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    const global = withPlugins(getLocalVue(true), pinia);
    // The link is stubbed, so seed the history it would otherwise fetch.
    useHistoryStore(pinia).setHistories([history]);

    return mount(TargetHistorySelector, {
        props: { targetHistoryId: history.id },
        global: {
            ...global,
            stubs: { ...global.stubs, SelectorModal: true, TargetHistoryLink: true },
        },
    });
}

describe("TargetHistorySelector", () => {
    it.each([
        {
            state: "archived",
            history: { id: "archived-history", name: "Archived History", archived: true },
            warning: "This history has been archived and cannot receive uploads.",
        },
        {
            state: "deleted",
            history: { id: "deleted-history", name: "Deleted History", deleted: true },
            warning: "This history has been deleted and cannot receive uploads.",
        },
    ])("shows a warning for a $state history", ({ history, warning }) => {
        const wrapper = mountWithHistory(history);

        expect(wrapper.getComponent(GAlert).text()).toContain(warning);
    });

    it("does not show a warning for an active history", () => {
        const wrapper = mountWithHistory();

        expect(wrapper.getComponent(TargetHistoryLink).props("targetHistoryId")).toBe("active-history");
        expect(wrapper.findComponent(GAlert).exists()).toBe(false);
        expect(wrapper.text()).not.toContain("cannot receive uploads");
    });
});
