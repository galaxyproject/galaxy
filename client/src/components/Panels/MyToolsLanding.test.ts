import { getFakeRegisteredUser } from "@tests/test-data";
import { getFakeTool } from "@tests/test-data/tools";
import { getLocalVue, nth, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { FavoriteOrderEntry } from "@/stores/users/queries";
import { useUserStore } from "@/stores/userStore";

import MyToolsLanding from "./MyToolsLanding.vue";

vi.mock("@/composables/config");

const localVue = getLocalVue();

const SELECTORS = {
    FAVORITES_LIST: "[data-description='favorites-top-level-list']",
    FAVORITE_ITEM: ".favorite-top-level-item",
} as const;

const TOOLS = {
    cat1: getFakeTool({ id: "cat1", name: "cat1" }),
    cat2: getFakeTool({ id: "cat2", name: "cat2" }),
};

interface SortableHandlers {
    options: Record<string, (evt: unknown) => void>;
}

enableAutoUnmount(afterEach);

function mountWithFavoriteTools(order: FavoriteOrderEntry[]) {
    const pinia = createPinia();
    setActivePinia(pinia);
    const userStore = useUserStore();
    userStore.setCurrentUser(getFakeRegisteredUser());
    userStore.currentPreferences = { favorites: { tools: ["cat1", "cat2"], order } };
    const reorderFavorites = vi.spyOn(userStore, "reorderFavorites").mockResolvedValue();

    const wrapper = mount(MyToolsLanding, {
        global: withPlugins(localVue, pinia),
        attachTo: document.body,
        props: {
            localToolsById: TOOLS,
            defaultSectionsById: null,
            localSectionsById: {},
            toolsCount: 2,
        },
    });
    return { wrapper, reorderFavorites };
}

function favoriteItems(list: HTMLElement) {
    return Array.from(list.querySelectorAll<HTMLElement>(SELECTORS.FAVORITE_ITEM));
}

/**
 * Sortable is what turns a real drag into these callbacks; drive them directly
 * since happy-dom has no layout to hit-test a drag against.
 */
async function dragFavorite(list: HTMLElement, oldIndex: number, newIndex: number) {
    const sortableKey = Object.keys(list).find((key) => key.startsWith("Sortable"))!;
    const { options } = (list as unknown as Record<string, SortableHandlers>)[sortableKey]!;
    const items = favoriteItems(list);
    const item = nth(items, oldIndex);
    const target = nth(items, newIndex);

    options.onStart!({ item, from: list, to: list, oldIndex });
    list.insertBefore(item, newIndex < oldIndex ? target : target.nextSibling);
    options.onUpdate!({ item, from: list, to: list, oldIndex, newIndex });
    options.onEnd!({ item, from: list, to: list, oldIndex, newIndex });
    await flushPromises();
}

describe("MyToolsLanding favorite reordering", () => {
    it("persists the dropped order of top-level favorites", async () => {
        const { wrapper, reorderFavorites } = mountWithFavoriteTools([
            { object_type: "tools", object_id: "cat1" },
            { object_type: "tools", object_id: "cat2" },
        ]);
        await flushPromises();
        const list = wrapper.find<HTMLElement>(SELECTORS.FAVORITES_LIST).element;
        expect(favoriteItems(list).map((item) => item.dataset.favoriteId)).toEqual(["cat1", "cat2"]);

        await dragFavorite(list, 1, 0);

        expect(reorderFavorites).toHaveBeenCalledWith([
            { object_type: "tools", object_id: "cat2" },
            { object_type: "tools", object_id: "cat1" },
        ]);
    });
});
