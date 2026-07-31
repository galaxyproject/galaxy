import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useHistoryStore } from "@/stores/historyStore";

import HistoryScrollList from "./HistoryScrollList.vue";

const localVue = getLocalVue(true);

vi.mock("vue-router/composables", () => ({
    useRouter: () => ({ push: vi.fn() }),
}));

/** A promise whose resolution this test controls, standing in for a slow request. */
function deferred() {
    let resolve!: () => void;
    const promise = new Promise<void>((r) => {
        resolve = r;
    });
    return { promise, resolve };
}

/** Mounts with no filter, so no request is made until the test asks for one. */
function mountList() {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);
    const wrapper = mount(HistoryScrollList as object, {
        propsData: { filter: "", loading: false, multiple: true, inModal: true },
        localVue,
        pinia,
        stubs: { ScrollList: true, GCard: true, BAlert: true, BBadge: true },
    });
    const store = useHistoryStore();
    return { wrapper, store, loadHistories: store.loadHistories as ReturnType<typeof vi.fn> };
}

describe("HistoryScrollList", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("searches again for text typed while a search is in flight", async () => {
        const first = deferred();
        const { wrapper, loadHistories } = mountList();
        loadHistories.mockImplementationOnce(() => first.promise);

        await wrapper.setProps({ filter: "alpha" });
        await flushPromises();
        expect(loadHistories).toHaveBeenCalledTimes(1);

        // The user keeps typing while that request is still outstanding.
        await wrapper.setProps({ filter: "alphabet" });
        await flushPromises();
        expect(loadHistories).toHaveBeenCalledTimes(1);

        first.resolve();
        await flushPromises();

        // Previously the in-flight guard dropped the second search outright,
        // leaving the list filtered by text whose results were never fetched,
        // which renders empty with nothing to select.
        expect(loadHistories).toHaveBeenCalledTimes(2);
        expect(loadHistories.mock.calls[1]?.[1]).toContain("alphabet");
    });

    it("does not re-query when the filter has not changed", async () => {
        const first = deferred();
        const { wrapper, loadHistories } = mountList();
        loadHistories.mockImplementationOnce(() => first.promise);

        await wrapper.setProps({ filter: "alpha" });
        await flushPromises();
        first.resolve();
        await flushPromises();

        expect(loadHistories).toHaveBeenCalledTimes(1);
    });

    it("does not re-query for a filter too short to search", async () => {
        const first = deferred();
        const { wrapper, loadHistories } = mountList();
        loadHistories.mockImplementationOnce(() => first.promise);

        await wrapper.setProps({ filter: "alpha" });
        await flushPromises();

        // Backspacing to under the minimum length is handled client-side.
        await wrapper.setProps({ filter: "al" });
        first.resolve();
        await flushPromises();

        expect(loadHistories).toHaveBeenCalledTimes(1);
    });
});
