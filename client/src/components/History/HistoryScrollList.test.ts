import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import HistoryScrollList from "./HistoryScrollList.vue";
import ScrollList from "@/components/ScrollList/ScrollList.vue";

const localVue = getLocalVue(true);

vi.mock("vue-router/composables", () => ({
    useRouter: () => ({ push: vi.fn() }),
}));

function makeHistories(n: number) {
    return Array.from({ length: n }, (_, i) => ({
        id: `h${i}`,
        name: `history ${i}`,
        archived: false,
        deleted: false,
        purged: false,
        published: false,
        annotation: "",
        count: 0,
        model_class: "History",
        tags: [],
        update_time: "2024-01-01T00:00:00Z",
        url: `/api/histories/h${i}`,
        user_id: "u1",
    }));
}

/** Mounts with no filter, so nothing is fetched until the test asks for it. */
function mountList(storedHistories?: unknown[]) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);
    const store = useHistoryStore();
    // The list only shows histories the current user owns.
    useUserStore().currentUser = { id: "u1", email: "u@x.y", isAnonymous: false } as never;
    if (storedHistories) {
        // Set the state directly: createTestingPinia stubs actions, and this
        // exercises what gets rendered rather than how it is fetched.
        store.storedHistories = Object.fromEntries(
            (storedHistories as { id: string }[]).map((h) => [h.id, h]),
        ) as never;
    }
    const wrapper = mount(HistoryScrollList as object, {
        propsData: { filter: "", loading: false, multiple: true, inModal: true },
        localVue,
        pinia,
        stubs: { GCard: true, BAlert: true },
    });
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

    it("renders a bounded window rather than every match", async () => {
        // The list is not virtualized, so handing ScrollList thousands of
        // matches puts thousands of cards in the DOM and stalls the panel.
        const { wrapper } = mountList(makeHistories(2000));
        await flushPromises();

        const scrollList = wrapper.findComponent(ScrollList);
        expect(scrollList.props("propItems")).toHaveLength(50);
    });

    it("reveals more matches when scrolled without refetching", async () => {
        const { wrapper, loadHistories } = mountList(makeHistories(2000));
        await flushPromises();

        const scrollList = wrapper.findComponent(ScrollList);
        scrollList.vm.$emit("load-more");
        await flushPromises();

        expect(scrollList.props("propItems")).toHaveLength(100);
        // Everything shown is already in memory, so nothing is fetched.
        expect(loadHistories).not.toHaveBeenCalled();
    });

    it("starts a new search back at the top of its own results", async () => {
        const { wrapper } = mountList(makeHistories(2000));
        await flushPromises();

        const scrollList = wrapper.findComponent(ScrollList);
        scrollList.vm.$emit("load-more");
        await flushPromises();
        expect(scrollList.props("propItems")).toHaveLength(100);

        await wrapper.setProps({ filter: "history 1" });
        await flushPromises();
        expect(scrollList.props("propItems")).toHaveLength(50);
    });
});
