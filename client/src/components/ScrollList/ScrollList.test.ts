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
const LOAD_MORE_BUTTON = "[data-description='load more items button']";
const TEST_ITEM_SLOT = '<div data-description="test item" slot-scope="{ item, index }">Test {{ item.name }}</div>';
const ITEM_NAME = "test item";
const ITEM_NAME_PLURAL = "test items";

function createTestItems(count: number): TestItem[] {
    const items = Array.from({ length: count }, (_, index) => ({
        id: `item-${index}`,
        name: `Item ${index + 1}`,
    }));
    return items;
}

/** The infinite scroll callback mock, given the same name as the callback in `ScrollList`. */
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

const TEST_ITEMS = createTestItems(TOTAL_ITEMS);

/** For the specific case where `propItems` is passed and updated by the loader,
 * we keep track of the expected total count to calculate changes that are unrelated
 * to scrolling/loading (e.g., an item or more added/removed externally in some other component). */
let expectedTotalItemCount = 0;

/** Returns `BUFFER_SIZE` items each time, given the current offset.
 *
 * Note: _The_ `wrapper` _parameter is optional and we use it to update `props.propItems`.
 * This serves to mock the behavior of the parent component updating the `propItems` (via a store for e.g.)._
 * @param offset The current offset to load items from.
 * @param limit The number of items to load.
 * @param wrapper Optional component wrapper to update the `propItems` with new items.
 */
const testLoader = jest.fn(
    (offset: number, limit: number, wrapper?: Wrapper<Vue>): Promise<{ items: TestItem[]; total: number }> => {
        const newItems = TEST_ITEMS.slice(offset, offset + limit);

        if (wrapper) {
            const currentPropItems = wrapper.props().propItems || [];

            // Calculate external changes: actual length vs what we expected before this load
            const externalChanges = currentPropItems.length - expectedTotalItemCount;

            // Update expected length for next call
            expectedTotalItemCount = currentPropItems.length + newItems.length;

            wrapper.setProps({
                propItems: [...(wrapper.props().propItems || []), ...newItems],
                propTotalCount: TOTAL_ITEMS + externalChanges,
            });
        }
        return Promise.resolve({
            items: newItems,
            total: TOTAL_ITEMS,
        });
    },
);

describe("ScrollList with local loader and data", () => {
    let wrapper: Wrapper<Vue>;

    beforeEach(async () => {
        wrapper = mount(ScrollList as object, {
            propsData: {
                loader: (offset: number, limit: number) => testLoader(offset, limit),
                itemKey: (item: TestItem) => item.id,
                limit: BUFFER_SIZE,
                name: "test item",
                namePlural: "test items",
            },
            localVue: getLocalVue(),
            scopedSlots: {
                item: TEST_ITEM_SLOT,
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

    it("shows item count and total items", async () => {
        await scrollOnce();
        expect(wrapper.text()).toContain(`Loaded ${BUFFER_SIZE} out of ${TOTAL_ITEMS} ${ITEM_NAME_PLURAL}`);

        await scrollOnce();
        await scrollOnce();
        expect(wrapper.text()).toContain(`Loaded ${BUFFER_SIZE * 3} out of ${TOTAL_ITEMS} ${ITEM_NAME_PLURAL}`);

        expect(wrapper.find(LOAD_MORE_BUTTON).exists()).toBe(true);

        while (wrapper.findAll(TEST_ITEM_DIV).length < TOTAL_ITEMS) {
            await scrollOnce();
        }
        expect(wrapper.text()).toContain(`- All ${ITEM_NAME_PLURAL} loaded -`);
        expect(wrapper.find(LOAD_MORE_BUTTON).exists()).toBe(false);

        // Now we test if the `showCountInFooter` prop works
        await wrapper.setProps({ showCountInFooter: true });
        expect(wrapper.text()).toContain(`- ${TOTAL_ITEMS} ${ITEM_NAME_PLURAL} loaded -`);
    });
});

describe("ScrollList with prop items and no local state", () => {
    let wrapper: Wrapper<Vue>;

    beforeEach(() => {
        wrapper = mount(ScrollList as object, {
            propsData: {
                propItems: TEST_ITEMS,
                propTotalCount: TOTAL_ITEMS,
                itemKey: (item: TestItem) => item.id,
                name: ITEM_NAME,
                namePlural: ITEM_NAME_PLURAL,
            },
            localVue: getLocalVue(),
            scopedSlots: {
                item: TEST_ITEM_SLOT,
            },
            stubs: {
                FontAwesomeIcon: true,
            },
        });
    });

    it("renders all items without scrolling/loading", async () => {
        // Assert that `propItems` is already populated
        expect(wrapper.props().propItems.length).toBe(TOTAL_ITEMS);

        expect(wrapper.findAll(TEST_ITEM_DIV).length).toBe(TOTAL_ITEMS);
        expect(wrapper.text()).toContain(`All ${ITEM_NAME_PLURAL} loaded`);
        expect(wrapper.find(LOAD_MORE_BUTTON).exists()).toBe(false);

        // We try to scroll, but since there are no items to load, the loader should not be called
        await scrollOnce();
        expect(testLoader).toHaveBeenCalledTimes(0);
    });
});

describe("ScrollList with prop items and a local state loader", () => {
    let wrapper: Wrapper<Vue>;

    beforeEach(() => {
        expectedTotalItemCount = 0;

        wrapper = mount(ScrollList as object, {
            propsData: {
                // We make sure the `loader` updates the `propItems` (mock the loader loading via a pinia store for e.g.)
                loader: (offset: number, limit: number) => testLoader(offset, limit, wrapper),
                limit: BUFFER_SIZE,
                propItems: [],
                propTotalCount: TOTAL_ITEMS,
                itemKey: (item: TestItem) => item.id,
                name: ITEM_NAME,
                namePlural: ITEM_NAME_PLURAL,
                adjustForTotalCountChanges: false, // Default; we will adjust this to test this later
            },
            localVue: getLocalVue(),
            scopedSlots: {
                item: TEST_ITEM_SLOT,
            },
            stubs: {
                FontAwesomeIcon: true,
            },
        });
    });

    it("updates the propItems on scroll", async () => {
        // Assert that `propItems` is initially empty
        expect(wrapper.props().propItems.length).toBe(0);

        await scrollOnce();

        // First `BUFFER_SIZE` items should be loaded
        expect(wrapper.findAll(TEST_ITEM_DIV).length).toBe(BUFFER_SIZE);

        // And the `propItems` have been updated as well
        expect(wrapper.props().propItems.length).toBe(BUFFER_SIZE);

        // And this happened through the loader
        expect(testLoader).toHaveBeenCalledTimes(1);

        // Next, we scroll twice more to find a total of `BUFFER_SIZE * 3` items
        await scrollOnce();
        await scrollOnce();
        expect(wrapper.findAll(TEST_ITEM_DIV).length).toBe(BUFFER_SIZE * 3);
        expect(wrapper.props().propItems.length).toBe(BUFFER_SIZE * 3);
        expect(testLoader).toHaveBeenCalledTimes(3);
    });

    it("handles the count change discrepancy between propItems and local state", async () => {
        // Initially, propItems is empty, so the count should be 0
        expect(wrapper.text()).toContain(`Loaded 0 out of ${TOTAL_ITEMS} ${ITEM_NAME_PLURAL}`);

        await scrollOnce();

        // After loading first BUFFER_SIZE items, the count should be updated via the loader
        expect(wrapper.text()).toContain(`Loaded ${BUFFER_SIZE} out of ${TOTAL_ITEMS} ${ITEM_NAME_PLURAL}`);
        expect(testLoader).toHaveBeenCalledTimes(1);

        // Mock a change in the propItems (e.g., a store update like added/removed item) which is unrelated to scroll fetching
        // and DOESN'T UPDATE `propTotalCount`
        await wrapper.setProps({
            propItems: [...(wrapper.props().propItems || []), { id: "extra-item", name: "Extra Item" }],
        });

        // Confirm that this did not happen via the loader
        expect(testLoader).toHaveBeenCalledTimes(1);

        // The count is initially not handled correctly; current count updates but total count remains the same
        expect(wrapper.text()).toContain(`Loaded ${BUFFER_SIZE + 1} out of ${TOTAL_ITEMS} ${ITEM_NAME_PLURAL}`);

        // Now we trigger the adjustment for total count changes
        await wrapper.setProps({ adjustForTotalCountChanges: true });

        // The count should now reflect the total items correctly
        expect(wrapper.text()).toContain(`Loaded ${BUFFER_SIZE + 1} out of ${TOTAL_ITEMS + 1} ${ITEM_NAME_PLURAL}`);

        // Scroll again to load more items and check the count
        await scrollOnce();
        expect(testLoader).toHaveBeenCalledTimes(2);

        // This is a very important assertion:
        // It confirms that after the external change, the loader loads the correct number of items
        // from the correct offset, and that the loader's total count is adjusted correctly
        // meaning there is no discrepancy between the propItems and the local state's counts.
        // (So the `adjustForTotalCountChanges` did not come into play here).

        expect(wrapper.text()).toContain(`Loaded ${BUFFER_SIZE * 2 + 1} out of ${TOTAL_ITEMS + 1} ${ITEM_NAME_PLURAL}`);

        // We confirm that the adjustment based on `adjustForTotalCountChanges` in the `totalItemCount` computed was not calculated
        // here, since localItems and propItems are in sync.
        await wrapper.setProps({ adjustForTotalCountChanges: false });

        expect(wrapper.text()).toContain(`Loaded ${BUFFER_SIZE * 2 + 1} out of ${TOTAL_ITEMS + 1} ${ITEM_NAME_PLURAL}`);
    });
});
