import { getLocalVue } from "@tests/jest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import { nextTick } from "vue";

import ScrollList from "./ScrollList.vue";

interface TestItem {
    id: string;
    name: string;
}

const TOTAL_ITEMS = 50;
const BUFFER_SIZE = 5;
const TEST_ITEM_DIV = "div[data-description='test item']";

function createTestItems(count: number): TestItem[] {
    const items = Array.from({ length: count }, (_, index) => ({
        id: `item-${index}`,
        name: `Item ${index + 1}`,
    }));
    return items;
}

/** The infinite scroll callback, given the same name as the callback in `ScrollList`. */
let loadItems: (() => void) | null = null;

// Mock useInfiniteScroll to store the component's callback in the callback here
jest.mock("@vueuse/core", () => ({
    ...jest.requireActual("@vueuse/core"),
    useInfiniteScroll: jest.fn((element, callback) => {
        // On component mount, `useInfiniteScroll` is called and here, we store the callback
        loadItems = callback;
        return {};
    }),
}));

/** Mocks a single scroll event to trigger the infinite scroll callback. */
async function scrollOnce() {
    if (loadItems) {
        loadItems();
        await new Promise((resolve) => setTimeout(resolve, 10));
        await nextTick();
    }
}

describe("ScrollList with local loader and data", () => {
    let wrapper: Wrapper<Vue>;
    const items = createTestItems(TOTAL_ITEMS);

    /** Returns `BUFFER_SIZE` items each time, given the current offset. */
    const testLoader = jest.fn((offset: number, limit: number): Promise<{ items: TestItem[]; total: number }> => {
        return Promise.resolve({
            items: items.slice(offset, offset + limit),
            total: items.length,
        });
    });

    beforeEach(async () => {
        wrapper = mount(ScrollList as object, {
            propsData: {
                loader: (offset: number, limit: number) => testLoader(offset, limit),
                itemKey: (item: TestItem) => item.id,
                limit: BUFFER_SIZE,
            },
            localVue: getLocalVue(),
            scopedSlots: {
                item: '<div data-description="test item" slot-scope="{ item, index }">Test {{ item.name }}</div>',
            },
            stubs: {
                FontAwesomeIcon: true,
            },
        });
    });

    it("loads items on scroll", async () => {
        await scrollOnce();

        // First `BUFFER_SIZE` items should be loaded
        const items = wrapper.findAll(TEST_ITEM_DIV);
        expect(items.length).toBe(BUFFER_SIZE);

        // Next, we scroll twice more to find a total of `BUFFER_SIZE * 3` items
        await scrollOnce();
        await scrollOnce();
        expect(wrapper.findAll(TEST_ITEM_DIV).length).toBe(BUFFER_SIZE * 3);

        // Confirm that that the loader (testLoader) was called thrice (since we call `scrollOnce` 3 times)
        expect(testLoader).toHaveBeenCalledTimes(3);

        // Then we scroll until all items are loaded
        while (wrapper.findAll(TEST_ITEM_DIV).length < TOTAL_ITEMS) {
            await scrollOnce();
        }
        expect(wrapper.findAll(TEST_ITEM_DIV).length).toBe(TOTAL_ITEMS);

        // Confirm that the loader was called enough times to load all items
        expect(testLoader).toHaveBeenCalledTimes(Math.ceil(TOTAL_ITEMS / BUFFER_SIZE));

        // Check that even if we scroll again, no new items are loaded
        await scrollOnce();
        expect(wrapper.findAll(TEST_ITEM_DIV).length).toBe(TOTAL_ITEMS);
        expect(testLoader).toHaveBeenCalledTimes(Math.ceil(TOTAL_ITEMS / BUFFER_SIZE));
    });
});
