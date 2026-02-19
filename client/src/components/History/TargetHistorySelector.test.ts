import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { describe, expect, it } from "vitest";

import type { HistorySummary } from "@/api";
import { useHistoryStore } from "@/stores/historyStore";

import TargetHistorySelector from "./TargetHistorySelector.vue";

const localVue = getLocalVue();

const mockHistory: HistorySummary = {
    id: "mock-history",
    name: "Mock History",
    archived: false,
    deleted: false,
    annotation: "",
    count: 0,
    model_class: "History",
    published: false,
    purged: false,
    tags: [],
    update_time: "2024-01-01T00:00:00Z",
    url: "/api/histories/mock-history",
};

async function mountWithHistory(history: HistorySummary) {
    const pinia = createPinia();

    const wrapper = mount(TargetHistorySelector as object, {
        propsData: {
            targetHistoryId: history.id,
        },
        localVue,
        pinia,
        stubs: {
            SelectorModal: true,
            TargetHistoryLink: true,
        },
    });

    const historyStore = useHistoryStore();
    historyStore.setHistory(history as any);

    await wrapper.vm.$nextTick();

    return wrapper;
}

describe("TargetHistorySelector", () => {
    it("shows warning for archived history", async () => {
        const wrapper = await mountWithHistory({
            ...mockHistory,
            id: "history-archived",
            name: "Archived History",
            archived: true,
            deleted: false,
        });

        expect(wrapper.text()).toContain("This history has been archived and cannot receive uploads.");
    });

    it("shows warning for deleted history", async () => {
        const wrapper = await mountWithHistory({
            ...mockHistory,
            id: "history-deleted",
            name: "Deleted History",
            archived: false,
            deleted: true,
        });

        expect(wrapper.text()).toContain("This history has been deleted and cannot receive uploads.");
    });

    it("does not show warning for active history", async () => {
        const wrapper = await mountWithHistory({
            ...mockHistory,
            id: "history-active",
            name: "Active History",
            archived: false,
            deleted: false,
        });

        expect(wrapper.text()).not.toContain("cannot receive uploads");
    });
});
