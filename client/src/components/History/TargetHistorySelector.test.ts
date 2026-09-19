import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";

import type { HistorySummary } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";

import TargetHistorySelector from "./TargetHistorySelector.vue";

const localVue = getLocalVue(true);

const { server, http } = useServerMock();

const ACTIVE_HISTORY: HistorySummary = {
    id: "active-history",
    name: "Active History",
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

const ARCHIVED_HISTORY: HistorySummary = {
    ...ACTIVE_HISTORY,
    id: "archived-history",
    name: "Archived History",
    archived: true,
};

const DELETED_HISTORY: HistorySummary = {
    ...ACTIVE_HISTORY,
    id: "deleted-history",
    name: "Deleted History",
    deleted: true,
};

async function mountWithHistory(history: HistorySummary) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);

    server.use(
        http.get("/api/histories/{history_id}", ({ response }) => {
            return response(200).json(history);
        }),
    );

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

    await flushPromises();

    return wrapper;
}

describe("TargetHistorySelector", () => {
    it("shows warning for archived history", async () => {
        const wrapper = await mountWithHistory(ARCHIVED_HISTORY);

        expect(wrapper.text()).toContain("This history has been archived and cannot receive uploads.");
    });

    it("shows warning for deleted history", async () => {
        const wrapper = await mountWithHistory(DELETED_HISTORY);

        expect(wrapper.text()).toContain("This history has been deleted and cannot receive uploads.");
    });

    it("does not show warning for active history", async () => {
        const wrapper = await mountWithHistory(ACTIVE_HISTORY);

        expect(wrapper.text()).not.toContain("cannot receive uploads");
    });
});
