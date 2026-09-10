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

function makeHistories(count: number) {
    return Array.from({ length: count }, (_, i) => ({
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
        // Ascending update_time, so the unpinned order is h2, h1, h0.
        update_time: `2024-01-0${i + 1}T00:00:00Z`,
        url: `/api/histories/h${i}`,
        user_id: "u1",
    }));
}

/** Mounts the multiview variant of the list with `pinned` already pinned. */
function mountList(pinned: string[]) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);
    const store = useHistoryStore();
    useUserStore().currentUser = { id: "u1", email: "a@b.c", isAnonymous: false } as never;
    store.storedHistories = Object.fromEntries(makeHistories(3).map((h) => [h.id, h])) as never;
    store.pinnedHistories = pinned.map((id) => ({ id }));
    const wrapper = mount(HistoryScrollList as object, {
        // multiple + not in a modal is the multiview panel, where pinned
        // histories are sorted to the top.
        propsData: { filter: "", loading: false, multiple: true, inModal: false },
        localVue,
        pinia,
        stubs: { GCard: true, BAlert: true },
    });
    return { wrapper, store };
}

function renderedIds(wrapper: ReturnType<typeof mount>) {
    return (wrapper.findComponent(ScrollList).props("propItems") as { id: string }[]).map((h) => h.id);
}

describe("HistoryScrollList pinned ordering", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("sorts pinned histories to the top", async () => {
        const { wrapper } = mountList(["h0"]);
        await flushPromises();
        expect(renderedIds(wrapper)[0]).toBe("h0");
    });

    it("leaves a history in place when it is deselected", async () => {
        const { wrapper, store } = mountList(["h0"]);
        await flushPromises();
        const before = renderedIds(wrapper);
        expect(before[0]).toBe("h0");

        // Unpinning must not reorder the list under the cursor: previously the
        // row jumped down and the list scrolled to follow it.
        store.pinnedHistories = [];
        await flushPromises();

        expect(renderedIds(wrapper)).toEqual(before);
    });

    it("re-sorts once the search text changes", async () => {
        const { wrapper, store } = mountList(["h0"]);
        await flushPromises();
        store.pinnedHistories = [];
        await flushPromises();
        expect(renderedIds(wrapper)[0]).toBe("h0");

        // A new search is a legitimate reason to reorder, so the frozen order
        // is refreshed and h0 falls back to its update_time position.
        await wrapper.setProps({ filter: "history" });
        await flushPromises();

        expect(renderedIds(wrapper)[0]).not.toBe("h0");
    });
});
