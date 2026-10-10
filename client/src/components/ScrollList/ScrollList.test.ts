import { composeStories } from "@storybook/vue3-vite";
import { getLocalVue } from "@tests/vitest/helpers";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import { mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";
import type { Component, ComponentPublicInstance } from "vue";

import * as ScrollListStories from "./ScrollList.stories";

import ScrollList from "./ScrollList.vue";

const stories = composeStories(ScrollListStories);
const mountStory = useStoryMount();

const pageOfItems = stories.PagedFromLoader.args.loader!;
const BUFFER_SIZE = stories.PagedFromLoader.args.limit!;
const ITEM_NAME_PLURAL = stories.PagedFromLoader.args.namePlural;
const TOTAL_ITEMS = stories.GivenItems.args.propItems!.length;
const SCROLLS_TO_LOAD_ALL = Math.ceil(TOTAL_ITEMS / BUFFER_SIZE);

const LIST_ITEM = "[data-description='scroll list item']";
const ADD_ITEM_BUTTON = "[data-description='add item button']";
const LOAD_MORE_BUTTON = "[data-description='load more items button']";

/** The callback ScrollList registers with `useInfiniteScroll`, invoked when the list is scrolled to its end. */
let onScrolledToEnd: (() => Promise<void>) | null = null;

vi.mock("@vueuse/core", async () => ({
    ...(await vi.importActual("@vueuse/core")),
    useInfiniteScroll: vi.fn((_element, callback) => {
        onScrolledToEnd = callback;
        return {};
    }),
}));

beforeEach(() => {
    onScrolledToEnd = null;
});

/** ScrollList is generic, so vue-test-utils can't infer its props; declare the one these tests read. */
function findScrollList(root: VueWrapper) {
    return root.findComponent(ScrollList) as VueWrapper<ComponentPublicInstance<{ propItems?: unknown[] }>>;
}

async function scrollToEnd(times = 1) {
    for (let i = 0; i < times; i++) {
        if (!onScrolledToEnd) {
            throw new Error("ScrollList did not register an infinite scroll callback.");
        }
        await onScrolledToEnd();
        await flushPromises();
    }
}

/** ScrollList keeps the loaded items itself; `loader` spies on the story's pages. */
function mountWithLocalLoader(story: StoryOf<typeof stories> = stories.PagedFromLoader) {
    const loader = vi.fn(pageOfItems);
    const wrapper = findScrollList(mountStory(story, { props: { loader } }));
    return { wrapper, loader };
}

/** The story's store owns the items; `loader` spies on the pages it fetches. */
function mountWithStoreLoader(props: { adjustForTotalCountChanges?: boolean } = {}) {
    const loader = vi.fn(stories.StoreOwnedItems.args.fetchPage!);
    const root = mountStory(stories.StoreOwnedItems, { props: { fetchPage: loader, ...props } });
    return {
        wrapper: findScrollList(root),
        loader,
        async addItemOutsideLoader() {
            await root.get(ADD_ITEM_BUTTON).trigger("click");
            await flushPromises();
        },
    };
}

function loadedText(loaded: number, total: number) {
    return `Loaded ${loaded} out of ${total} ${ITEM_NAME_PLURAL}`;
}

describe("ScrollList accessibility", () => {
    it("keeps footer messages out of the list and makes scrolling keyboard reachable", () => {
        const propItems = stories.GivenItems.args.propItems!.slice(0, 2);
        const wrapper = mountStory(stories.GivenItems, { props: { propItems, propTotalCount: 2 } });
        expect(wrapper.get(".scroll-list").attributes("tabindex")).toBe("0");
        expect(wrapper.get("[role='list']").findAll("[role='listitem']")).toHaveLength(2);
        expect(wrapper.get(".list-end").element.closest("[role='list']")).toBeNull();
        const top = wrapper.get("button[aria-label='Scroll to top']");
        expect(top.attributes("tabindex")).toBe("-1");
        expect(top.attributes("aria-disabled")).toBe("true");
    });
});

describe("ScrollList with local loader and data", () => {
    it("loads one page per scroll", async () => {
        const { wrapper, loader } = mountWithLocalLoader();

        await scrollToEnd();
        expect(wrapper.findAll(LIST_ITEM)).toHaveLength(BUFFER_SIZE);

        await scrollToEnd(2);
        expect(wrapper.findAll(LIST_ITEM)).toHaveLength(BUFFER_SIZE * 3);
        expect(loader).toHaveBeenCalledTimes(3);
    });

    it("stops loading once every item is loaded", async () => {
        const { wrapper, loader } = mountWithLocalLoader();

        await scrollToEnd(SCROLLS_TO_LOAD_ALL);
        expect(wrapper.findAll(LIST_ITEM)).toHaveLength(TOTAL_ITEMS);
        expect(loader).toHaveBeenCalledTimes(SCROLLS_TO_LOAD_ALL);

        await scrollToEnd();
        expect(wrapper.findAll(LIST_ITEM)).toHaveLength(TOTAL_ITEMS);
        expect(loader).toHaveBeenCalledTimes(SCROLLS_TO_LOAD_ALL);
    });

    it("stops auto-retrying on error until the user clicks Load More", async () => {
        const { wrapper, loader } = mountWithLocalLoader();
        await scrollToEnd();
        expect(loader).toHaveBeenCalledTimes(1);

        loader.mockRejectedValueOnce(new Error("Boom"));
        await scrollToEnd();
        expect(loader).toHaveBeenCalledTimes(2);

        await scrollToEnd(2);
        expect(loader).toHaveBeenCalledTimes(2);

        await wrapper.find(LOAD_MORE_BUTTON).trigger("click");
        await flushPromises();
        expect(loader).toHaveBeenCalledTimes(3);
        expect(wrapper.findAll(LIST_ITEM)).toHaveLength(BUFFER_SIZE * 2);
    });

    it("shows the loaded and total counts with a Load More button while loading", async () => {
        const { wrapper } = mountWithLocalLoader();

        await scrollToEnd();
        expect(wrapper.text()).toContain(loadedText(BUFFER_SIZE, TOTAL_ITEMS));

        await scrollToEnd(2);
        expect(wrapper.text()).toContain(loadedText(BUFFER_SIZE * 3, TOTAL_ITEMS));
        expect(wrapper.find(LOAD_MORE_BUTTON).exists()).toBe(true);
    });

    // Toggling a prop on a live mount needs `setProps`, which remounts a composed story, so this mounts
    // ScrollList directly with the story's args.
    it("replaces the Load More button with an all-loaded footer, showing the count when showCountInFooter is set", async () => {
        const wrapper = mount(ScrollList as Component, {
            props: { ...stories.PagedFromLoader.args },
            global: getLocalVue(),
        });
        onTestFinished(() => wrapper.unmount());

        await scrollToEnd(SCROLLS_TO_LOAD_ALL);
        expect(wrapper.text()).toContain(`- All ${ITEM_NAME_PLURAL} loaded -`);
        expect(wrapper.find(LOAD_MORE_BUTTON).exists()).toBe(false);

        await wrapper.setProps({ showCountInFooter: true });
        expect(wrapper.text()).toContain(`- ${TOTAL_ITEMS} ${ITEM_NAME_PLURAL} loaded -`);
    });

    it("shows the item count in the all-loaded footer from mount", async () => {
        const { wrapper } = mountWithLocalLoader(stories.CountInFooter);

        await scrollToEnd(SCROLLS_TO_LOAD_ALL);
        expect(wrapper.text()).toContain(`- ${TOTAL_ITEMS} ${ITEM_NAME_PLURAL} loaded -`);
        expect(wrapper.find(LOAD_MORE_BUTTON).exists()).toBe(false);
    });
});

describe("ScrollList with prop items and no loader", () => {
    it("renders all prop items and requests nothing more on scroll", async () => {
        const wrapper = findScrollList(mountStory(stories.GivenItems));

        expect(wrapper.props().propItems).toHaveLength(TOTAL_ITEMS);
        expect(wrapper.findAll(LIST_ITEM)).toHaveLength(TOTAL_ITEMS);
        expect(wrapper.text()).toContain(`All ${ITEM_NAME_PLURAL} loaded`);
        expect(wrapper.find(LOAD_MORE_BUTTON).exists()).toBe(false);

        await scrollToEnd();
        expect(wrapper.emitted("load-more")).toBeUndefined();
    });
});

describe("ScrollList with prop items and a store-backed loader", () => {
    it("loads each page through the loader into propItems", async () => {
        const { wrapper, loader } = mountWithStoreLoader();
        expect(wrapper.props().propItems).toHaveLength(0);

        await scrollToEnd();
        expect(wrapper.findAll(LIST_ITEM)).toHaveLength(BUFFER_SIZE);
        expect(wrapper.props().propItems).toHaveLength(BUFFER_SIZE);
        expect(loader).toHaveBeenCalledTimes(1);

        await scrollToEnd(2);
        expect(wrapper.findAll(LIST_ITEM)).toHaveLength(BUFFER_SIZE * 3);
        expect(wrapper.props().propItems).toHaveLength(BUFFER_SIZE * 3);
        expect(loader).toHaveBeenCalledTimes(3);
    });

    it("adjusts the total for an item added outside the loader until the next load", async () => {
        const { wrapper, loader, addItemOutsideLoader } = mountWithStoreLoader();
        expect(wrapper.text()).toContain(loadedText(0, TOTAL_ITEMS));

        await scrollToEnd();
        expect(wrapper.text()).toContain(loadedText(BUFFER_SIZE, TOTAL_ITEMS));
        expect(loader).toHaveBeenCalledTimes(1);

        await addItemOutsideLoader();
        expect(loader).toHaveBeenCalledTimes(1);
        expect(wrapper.text()).toContain(loadedText(BUFFER_SIZE + 1, TOTAL_ITEMS + 1));

        // The next page's total already counts the added item.
        await scrollToEnd();
        expect(loader).toHaveBeenCalledTimes(2);
        expect(wrapper.text()).toContain(loadedText(BUFFER_SIZE * 2 + 1, TOTAL_ITEMS + 1));
    });

    // Toggling a prop on a live mount needs `setProps`, which remounts a composed story, so this mounts the
    // story's harness directly. It passes `adjustForTotalCountChanges` through to ScrollList as an attr.
    it("recomputes the total when adjustForTotalCountChanges is toggled on a live list", async () => {
        const loader = vi.fn(stories.StoreOwnedItems.args.fetchPage!);
        const root = mount(ScrollListStories.ScrollListWithStore as Component, {
            props: { ...stories.StoreOwnedItems.args, fetchPage: loader, adjustForTotalCountChanges: false },
            global: getLocalVue(),
        });
        onTestFinished(() => root.unmount());
        const wrapper = findScrollList(root);
        expect(wrapper.text()).toContain(loadedText(0, TOTAL_ITEMS));

        await scrollToEnd();
        expect(wrapper.text()).toContain(loadedText(BUFFER_SIZE, TOTAL_ITEMS));
        expect(loader).toHaveBeenCalledTimes(1);

        await root.get(ADD_ITEM_BUTTON).trigger("click");
        await flushPromises();
        expect(loader).toHaveBeenCalledTimes(1);
        expect(wrapper.text()).toContain(loadedText(BUFFER_SIZE + 1, TOTAL_ITEMS));

        await root.setProps({ adjustForTotalCountChanges: true });
        expect(wrapper.text()).toContain(loadedText(BUFFER_SIZE + 1, TOTAL_ITEMS + 1));

        // The next page's total already counts the added item, so the counts agree with or without the adjustment.
        await scrollToEnd();
        expect(loader).toHaveBeenCalledTimes(2);
        expect(wrapper.text()).toContain(loadedText(BUFFER_SIZE * 2 + 1, TOTAL_ITEMS + 1));

        await root.setProps({ adjustForTotalCountChanges: false });
        expect(wrapper.text()).toContain(loadedText(BUFFER_SIZE * 2 + 1, TOTAL_ITEMS + 1));
    });
});
