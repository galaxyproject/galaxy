import type { Decorator, Meta, StoryObj } from "@storybook/vue3-vite";
import { type Component, defineComponent, h, type PropType, ref } from "vue";

import ScrollList from "./ScrollList.vue";
import GButton from "@/components/BaseComponents/GButton.vue";

interface Item {
    id: string;
    name: string;
}

type Page = { items: Item[]; total: number };
type PageLoader = (offset: number, limit: number) => Promise<Page>;

const ITEMS: Item[] = Array.from({ length: 50 }, (_, index) => ({ id: `item-${index}`, name: `Dataset ${index + 1}` }));

/** Answers like a paged API: `limit` items from `offset`, plus the total. */
const pageOfItems: PageLoader = (offset, limit) =>
    Promise.resolve({ items: ITEMS.slice(offset, offset + limit), total: ITEMS.length });

/** Each item as a plain row. */
const itemSlot = {
    item: ({ item }: { item: Item }) => h("div", { "data-description": "scroll list item" }, item.name),
};

/**
 * Owns the items as a store would: each page `fetchPage` returns is appended to `propItems`.
 * "Add item" adds one outside the loader, as when a store learns of a new item; the server's
 * total counts it only from the next page on.
 */
export const ScrollListWithStore = defineComponent({
    name: "ScrollListWithStore",
    inheritAttrs: false,
    props: {
        fetchPage: { type: Function as PropType<PageLoader>, required: true },
        /** The total until the first page answers. */
        propTotalCount: { type: Number, default: undefined },
    },
    setup(props, { attrs, slots }) {
        const storeItems = ref<Item[]>([]);
        const storeTotal = ref(props.propTotalCount);
        let addedOutsideLoader = 0;

        async function loader(offset: number, limit: number) {
            const page = await props.fetchPage(offset, limit);
            storeItems.value = [...storeItems.value, ...page.items];
            storeTotal.value = page.total + addedOutsideLoader;
            return page;
        }

        function addItem() {
            addedOutsideLoader++;
            storeItems.value = [
                ...storeItems.value,
                { id: `added-${addedOutsideLoader}`, name: `Added dataset ${addedOutsideLoader}` },
            ];
        }

        return () =>
            h(
                ScrollList as Component,
                { ...attrs, loader, propItems: storeItems.value, propTotalCount: storeTotal.value },
                {
                    ...slots,
                    "footer-button-area": () =>
                        h(
                            GButton,
                            { size: "small", "data-description": "add item button", onClick: addItem },
                            () => "Add item",
                        ),
                },
            );
    },
});

/** A list scrolls only inside a parent of fixed height. */
const inFixedHeight: Decorator = (story) => ({
    render: () => h("div", { style: "height: 300px; display: flex; flex-direction: column" }, [h(story())]),
});

/**
 * ScrollList is generic, so stories type its props for `Item`, plus the store harness's `fetchPage`.
 * The meta has no `component` for the same reason: Storybook can't type a generic SFC.
 */
type Args = Parameters<typeof ScrollList<Item>>[0] & { fetchPage?: PageLoader };

const meta = {
    title: "ScrollList",
    excludeStories: ["ScrollListWithStore"],
    render: (args) => () => h(ScrollList as Component, args, itemSlot),
    decorators: [inFixedHeight],
    args: {
        itemKey: (item: Item) => item.id,
        limit: 5,
        name: "dataset",
        namePlural: "datasets",
    },
} satisfies Meta<Args>;

export default meta;
type Story = StoryObj<typeof meta>;

/** ScrollList keeps the items, loading five at a time as the list is scrolled. */
export const PagedFromLoader: Story = { args: { loader: pageOfItems } };

/** The all-loaded footer shows the item count instead of "All". */
export const CountInFooter: Story = { args: { ...PagedFromLoader.args, showCountInFooter: true } };

/** Every item is given up front, so nothing is left to load. */
export const GivenItems: Story = { args: { propItems: ITEMS, propTotalCount: ITEMS.length } };

/** A store owns the items and the loader feeds it; the total follows items added outside the loader. */
export const StoreOwnedItems: Story = {
    render: (args) => () => h(ScrollListWithStore as Component, args, itemSlot),
    args: { fetchPage: pageOfItems, propTotalCount: ITEMS.length, adjustForTotalCountChanges: true },
};
