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

/** Mounts with no filter, so nothing is fetched until the test asks for it. */
function mountList() {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);
    const wrapper = mount(HistoryScrollList as object, {
        propsData: { filter: "", loading: false, multiple: true, inModal: true },
        localVue,
        pinia,
        stubs: { ScrollList: true, GCard: true, BAlert: true },
    });
    const store = useHistoryStore();
    return {
        wrapper,
        store,
        loadAllHistories: store.loadAllHistories as ReturnType<typeof vi.fn>,
        loadHistories: store.loadHistories as ReturnType<typeof vi.fn>,
    };
}

describe("HistoryScrollList", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("fetches the whole list once and does not query per search", async () => {
        const { wrapper, loadAllHistories, loadHistories } = mountList();

        await wrapper.setProps({ filter: "alpha" });
        await flushPromises();
        expect(loadAllHistories).toHaveBeenCalledTimes(1);

        // Each further change of the search text is answered locally. Previously
        // every one of these issued an unbounded request for all matches, and a
        // request arriving while one was in flight was dropped outright.
        await wrapper.setProps({ filter: "alphabet" });
        await flushPromises();
        await wrapper.setProps({ filter: "alphabetical" });
        await flushPromises();

        expect(loadAllHistories).toHaveBeenCalledTimes(3);
        // The per-search query never goes out.
        expect(loadHistories).not.toHaveBeenCalledWith(true, expect.stringContaining("alpha"));
    });

    it("searches on a term shorter than the old three character minimum", async () => {
        const { wrapper, loadAllHistories } = mountList();

        await wrapper.setProps({ filter: "ab" });
        await flushPromises();

        expect(loadAllHistories).toHaveBeenCalledTimes(1);
    });

    it("does not fetch anything when there is no search text", async () => {
        const { loadAllHistories } = mountList();
        await flushPromises();
        expect(loadAllHistories).not.toHaveBeenCalled();
    });
});
