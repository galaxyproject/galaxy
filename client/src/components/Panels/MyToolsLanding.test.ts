import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Tool } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";

import MyToolsLanding from "./MyToolsLanding.vue";

vi.mock("@/composables/config");

const localVue = getLocalVue();

function makeTool(id: string): Tool {
    return { id, name: id, description: "", version: "1.0", model_class: "Tool" } as unknown as Tool;
}

const TOOLS = { cat1: makeTool("cat1"), cat2: makeTool("cat2") };
const FAVORITE_ORDER = [
    { object_type: "tools", object_id: "cat1" },
    { object_type: "tools", object_id: "cat2" },
];

interface SortableHandlers {
    options: Record<string, (evt: unknown) => void>;
}

describe("MyToolsLanding favorite reordering", () => {
    let wrapper: ReturnType<typeof mount> | undefined;

    afterEach(() => {
        wrapper?.unmount();
    });

    it("persists the dropped order of top-level favorites", async () => {
        const pinia = createPinia();
        setActivePinia(pinia);
        const userStore = useUserStore();
        userStore.setCurrentUser(getFakeRegisteredUser());
        userStore.currentPreferences = { favorites: { tools: ["cat1", "cat2"], order: FAVORITE_ORDER } } as never;
        const reorderFavorites = vi.spyOn(userStore, "reorderFavorites").mockResolvedValue();

        wrapper = mount(MyToolsLanding as object, {
            localVue,
            pinia,
            attachTo: document.body,
            propsData: {
                localToolsById: TOOLS,
                defaultSectionsById: null,
                localSectionsById: {},
                toolsCount: 2,
            },
        });
        await flushPromises();

        const list = document.querySelector<HTMLElement>('[data-description="favorites-top-level-list"]')!;
        const items = Array.from(list.querySelectorAll<HTMLElement>(".favorite-top-level-item"));
        expect(items.map((item) => item.dataset.favoriteId)).toEqual(["cat1", "cat2"]);

        // Sortable is what turns a real drag into these callbacks; drive them
        // directly since happy-dom has no layout to hit-test a drag against.
        const sortableKey = Object.keys(list).find((key) => key.startsWith("Sortable"))!;
        const { options } = (list as unknown as Record<string, SortableHandlers>)[sortableKey]!;
        const [first, second] = items as [HTMLElement, HTMLElement];

        options.onStart!({ item: second, from: list, to: list, oldIndex: 1 });
        list.insertBefore(second, first);
        options.onUpdate!({ item: second, from: list, to: list, oldIndex: 1, newIndex: 0 });
        options.onEnd!({ item: second, from: list, to: list, oldIndex: 1, newIndex: 0 });
        await flushPromises();

        expect(reorderFavorites).toHaveBeenCalledWith([
            { object_type: "tools", object_id: "cat2" },
            { object_type: "tools", object_id: "cat1" },
        ]);
    });
});
