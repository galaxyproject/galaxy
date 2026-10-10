import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ComponentPublicInstance } from "vue";

import ScrollList from "./ScrollList.vue";

interface TestItem {
    id: string;
    name: string;
}

type LoaderResult = { items: TestItem[]; total: number };

const TOTAL_ITEMS = 50;
const BUFFER_SIZE = 5;
const SCROLLS_TO_LOAD_ALL = Math.ceil(TOTAL_ITEMS / BUFFER_SIZE);
const ITEM_NAME = "test item";
const ITEM_NAME_PLURAL = "test items";

const TEST_ITEM_DIV = "div[data-description='test item']";
const LOAD_MORE_BUTTON = "[data-description='load more items button']";
const TEST_ITEM_SLOT = `<template #default="{ item }"><div data-description="test item">Test {{ item.name }}</div></template>`;

const TEST_ITEMS: TestItem[] = Array.from({ length: TOTAL_ITEMS }, (_, index) => ({
    id: `item-${index}`,
    name: `Item ${index + 1}`,
}));

/** ScrollList is generic, so vue-test-utils can't infer its props; declare the ones these tests read or set. */
type ScrollListWrapper = VueWrapper<
    ComponentPublicInstance<{
        propItems?: TestItem[];
        propTotalCount?: number;
        adjustForTotalCountChanges?: boolean;
        showCountInFooter?: boolean;
    }>
>;

/** The callback ScrollList registers with `useInfiniteScroll`, invoked when the list is scrolled to its end. */
let onScrolledToEnd: (() => Promise<void>) | null = null;

vi.mock("@vueuse/core", async () => ({
    ...(await vi.importActual("@vueuse/core")),
    useInfiniteScroll: vi.fn((_element, callback) => {
        onScrolledToEnd = callback;
        return {};
    }),
}));

enableAutoUnmount(afterEach);

beforeEach(() => {
    onScrolledToEnd = null;
});

async function scrollToEnd(times = 1) {
    for (let i = 0; i < times; i++) {
        if (!onScrolledToEnd) {
            throw new Error("ScrollList did not register an infinite scroll callback.");
        }
        await onScrolledToEnd();
        await flushPromises();
    }
}

function mountScrollList(props: Record<string, unknown>): ScrollListWrapper {
    const localVue = getLocalVue();
    return mount(ScrollList as object, {
        props: {
            itemKey: (item: TestItem) => item.id,
            name: ITEM_NAME,
            namePlural: ITEM_NAME_PLURAL,
            ...props,
        },
        slots: { item: TEST_ITEM_SLOT },
        global: {
            ...localVue,
            stubs: { ...localVue.stubs, FontAwesomeIcon: true },
        },
    }) as ScrollListWrapper;
}

/** ScrollList keeps the loaded items itself. */
function mountWithLocalLoader() {
    const loader = vi.fn(
        (offset: number, limit: number): Promise<LoaderResult> =>
            Promise.resolve({ items: TEST_ITEMS.slice(offset, offset + limit), total: TOTAL_ITEMS }),
    );
    const wrapper = mountScrollList({ loader, limit: BUFFER_SIZE });
    return { wrapper, loader };
}

/**
 * The parent owns the items, as a store would: each load appends a page to `propItems`, and
 * `propTotalCount` also counts items the parent added or removed since the previous load.
 */
function mountWithStoreLoader() {
    let expectedItemCount = 0;
    const loader = vi.fn((offset: number, limit: number): Promise<LoaderResult> => {
        const page = TEST_ITEMS.slice(offset, offset + limit);
        const currentItems = wrapper.props().propItems ?? [];
        const externalChanges = currentItems.length - expectedItemCount;
        expectedItemCount = currentItems.length + page.length;
        wrapper.setProps({
            propItems: [...currentItems, ...page],
            propTotalCount: TOTAL_ITEMS + externalChanges,
        });
        return Promise.resolve({ items: page, total: TOTAL_ITEMS });
    });
    const wrapper = mountScrollList({
        loader,
        limit: BUFFER_SIZE,
        propItems: [],
        propTotalCount: TOTAL_ITEMS,
        adjustForTotalCountChanges: false,
    });
    return { wrapper, loader };
}

function loadedText(loaded: number, total: number) {
    return `Loaded ${loaded} out of ${total} ${ITEM_NAME_PLURAL}`;
}

describe("ScrollList with local loader and data", () => {
    it("loads one page per scroll", async () => {
        const { wrapper, loader } = mountWithLocalLoader();

        await scrollToEnd();
        expect(wrapper.findAll(TEST_ITEM_DIV)).toHaveLength(BUFFER_SIZE);

        await scrollToEnd(2);
        expect(wrapper.findAll(TEST_ITEM_DIV)).toHaveLength(BUFFER_SIZE * 3);
        expect(loader).toHaveBeenCalledTimes(3);
    });

    it("stops loading once every item is loaded", async () => {
        const { wrapper, loader } = mountWithLocalLoader();

        await scrollToEnd(SCROLLS_TO_LOAD_ALL);
        expect(wrapper.findAll(TEST_ITEM_DIV)).toHaveLength(TOTAL_ITEMS);
        expect(loader).toHaveBeenCalledTimes(SCROLLS_TO_LOAD_ALL);

        await scrollToEnd();
        expect(wrapper.findAll(TEST_ITEM_DIV)).toHaveLength(TOTAL_ITEMS);
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
        expect(wrapper.findAll(TEST_ITEM_DIV)).toHaveLength(BUFFER_SIZE * 2);
    });

    it("shows the loaded and total counts with a Load More button while loading", async () => {
        const { wrapper } = mountWithLocalLoader();

        await scrollToEnd();
        expect(wrapper.text()).toContain(loadedText(BUFFER_SIZE, TOTAL_ITEMS));

        await scrollToEnd(2);
        expect(wrapper.text()).toContain(loadedText(BUFFER_SIZE * 3, TOTAL_ITEMS));
        expect(wrapper.find(LOAD_MORE_BUTTON).exists()).toBe(true);
    });

    it("replaces the Load More button with an all-loaded footer, showing the count when showCountInFooter is set", async () => {
        const { wrapper } = mountWithLocalLoader();

        await scrollToEnd(SCROLLS_TO_LOAD_ALL);
        expect(wrapper.text()).toContain(`- All ${ITEM_NAME_PLURAL} loaded -`);
        expect(wrapper.find(LOAD_MORE_BUTTON).exists()).toBe(false);

        await wrapper.setProps({ showCountInFooter: true });
        expect(wrapper.text()).toContain(`- ${TOTAL_ITEMS} ${ITEM_NAME_PLURAL} loaded -`);
    });
});

describe("ScrollList with prop items and no loader", () => {
    it("renders all prop items and requests nothing more on scroll", async () => {
        const wrapper = mountScrollList({ propItems: TEST_ITEMS, propTotalCount: TOTAL_ITEMS });

        expect(wrapper.props().propItems).toHaveLength(TOTAL_ITEMS);
        expect(wrapper.findAll(TEST_ITEM_DIV)).toHaveLength(TOTAL_ITEMS);
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
        expect(wrapper.findAll(TEST_ITEM_DIV)).toHaveLength(BUFFER_SIZE);
        expect(wrapper.props().propItems).toHaveLength(BUFFER_SIZE);
        expect(loader).toHaveBeenCalledTimes(1);

        await scrollToEnd(2);
        expect(wrapper.findAll(TEST_ITEM_DIV)).toHaveLength(BUFFER_SIZE * 3);
        expect(wrapper.props().propItems).toHaveLength(BUFFER_SIZE * 3);
        expect(loader).toHaveBeenCalledTimes(3);
    });

    it("adjusts the total for items added outside the loader only when adjustForTotalCountChanges is set", async () => {
        const { wrapper, loader } = mountWithStoreLoader();
        expect(wrapper.text()).toContain(loadedText(0, TOTAL_ITEMS));

        await scrollToEnd();
        expect(wrapper.text()).toContain(loadedText(BUFFER_SIZE, TOTAL_ITEMS));
        expect(loader).toHaveBeenCalledTimes(1);

        // The parent adds an item without updating propTotalCount.
        await wrapper.setProps({
            propItems: [...(wrapper.props().propItems ?? []), { id: "extra-item", name: "Extra Item" }],
        });
        expect(loader).toHaveBeenCalledTimes(1);
        expect(wrapper.text()).toContain(loadedText(BUFFER_SIZE + 1, TOTAL_ITEMS));

        await wrapper.setProps({ adjustForTotalCountChanges: true });
        expect(wrapper.text()).toContain(loadedText(BUFFER_SIZE + 1, TOTAL_ITEMS + 1));

        // The next load picks up from the new offset and its total already includes the extra
        // item, so the counts agree with or without the adjustment.
        await scrollToEnd();
        expect(loader).toHaveBeenCalledTimes(2);
        expect(wrapper.text()).toContain(loadedText(BUFFER_SIZE * 2 + 1, TOTAL_ITEMS + 1));

        await wrapper.setProps({ adjustForTotalCountChanges: false });
        expect(wrapper.text()).toContain(loadedText(BUFFER_SIZE * 2 + 1, TOTAL_ITEMS + 1));
    });
});
