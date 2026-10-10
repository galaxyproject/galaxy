import type { Decorator, Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, fn, waitFor } from "storybook/test";
import { type Component, defineComponent, h, type PropType, ref } from "vue";

import ScrollList from "./ScrollList.vue";
import GButton from "@/components/BaseComponents/GButton.vue";

interface Item {
    id: string;
    name: string;
}

type Page = { items: Item[]; total: number };
type PageLoader = (offset: number, limit: number) => Promise<Page>;

/** Items per page. */
const PAGE_SIZE = 5;

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
        limit: PAGE_SIZE,
        name: "dataset",
        namePlural: "datasets",
    },
} satisfies Meta<Args>;

export default meta;
type Story = StoryObj<typeof meta>;

type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

/** The names of the rows the list shows, in order. */
function rowNames({ canvas }: PlayContext) {
    return canvas.queryAllByText(/^(Added )?[Dd]ataset \d+$/).map((row) => row.textContent);
}

function firstNames(count: number) {
    return ITEMS.slice(0, count).map((item) => item.name);
}

function loadMoreButton({ canvas }: PlayContext) {
    return canvas.queryByRole("button", { name: /Load More/ });
}

/** The footer shown while rows are left to load, e.g. "Loaded 15 out of 50 datasets". */
async function expectLoadedCount({ canvas }: PlayContext, loaded: number, total: number) {
    await expect(canvas.getByText(/^Loaded \d+/)).toHaveTextContent(
        new RegExp(`^Loaded ${loaded} out of ${total} datasets$`),
    );
}

/** The region that scrolls the list, named for what it lists. */
function scroller({ canvas }: PlayContext) {
    return canvas.getByRole("region", { name: "datasets" });
}

/** Scrolls the list to its end, as a user would to see more; instantly, since the list scrolls smoothly. */
function scrollToEnd(context: PlayContext) {
    const list = scroller(context);
    list.scrollTo({ top: list.scrollHeight, behavior: "instant" });
}

/** Waits two animation frames, in which the list measures itself. */
function nextFrames() {
    return new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
}

/**
 * The list loads pages on its own until it can scroll. How many depends on the row height, so a play
 * waits for that and counts the rows instead of assuming a number.
 */
async function waitUntilFilled(context: PlayContext) {
    const list = scroller(context);
    await waitFor(() => expect(list.scrollHeight).toBeGreaterThan(list.clientHeight));
    // The list jumps back to the top a frame after it first can scroll; let that happen before scrolling.
    await nextFrames();
    await waitFor(() => expect(loadMoreButton(context)).not.toHaveAttribute("aria-disabled", "true"));
}

/** Scrolls page by page until all 50 rows are loaded, checking the rows and the count footer on the way. */
async function scrollUntilAllLoaded(context: PlayContext) {
    const { step } = context;
    await step("See the list fill its height, counting the loaded rows out of 50, with Load More offered", async () => {
        await waitUntilFilled(context);
        const loaded = rowNames(context).length;
        await expect(rowNames(context)).toEqual(firstNames(loaded));
        await expectLoadedCount(context, loaded, ITEMS.length);
        await expect(loadMoreButton(context)).toBeVisible();
    });
    while (rowNames(context).length < ITEMS.length) {
        const loaded = rowNames(context).length + PAGE_SIZE;
        await step(`Scroll to the end; rows up to ${loaded} load`, async () => {
            scrollToEnd(context);
            await waitFor(() => expect(rowNames(context)).toEqual(firstNames(loaded)));
            if (loaded < ITEMS.length) {
                await expectLoadedCount(context, loaded, ITEMS.length);
                await expect(loadMoreButton(context)).toBeVisible();
            }
        });
    }
}

/** ScrollList keeps the items, loading five at a time as the list is scrolled. */
export const PagedFromLoader: Story = {
    args: { loader: pageOfItems },
    // TODO a11y: aria-required-children, button-name (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** The all-loaded footer shows the item count instead of "All". */
export const CountInFooter: Story = {
    args: { ...PagedFromLoader.args, showCountInFooter: true },
    // TODO a11y: button-name (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Every item is given up front, so nothing is left to load. */
export const GivenItems: Story = {
    args: { propItems: ITEMS, propTotalCount: ITEMS.length },
    play: async (context) => {
        const { canvas, step } = context;
        await step("See all 50 given rows and the all-loaded footer, with no count or Load More", async () => {
            await expect(rowNames(context)).toEqual(firstNames(ITEMS.length));
            await expect(canvas.getByText("- All datasets loaded -")).toBeVisible();
            await expect(canvas.queryByText(/^Loaded \d+/)).not.toBeInTheDocument();
            await expect(loadMoreButton(context)).not.toBeInTheDocument();
        });
    },

    // TODO a11y: aria-required-children, button-name, scrollable-region-focusable (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** A store owns the items and the loader feeds it; the total follows items added outside the loader. */
export const StoreOwnedItems: Story = {
    render: (args) => () => h(ScrollListWithStore as Component, args, itemSlot),
    args: { fetchPage: pageOfItems, propTotalCount: ITEMS.length, adjustForTotalCountChanges: true },

    // TODO a11y: button-name (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Scrolling to the end loads the next page until every item is in, then the footer says so. */
export const LoadsEveryPageOnScroll: Story = {
    args: { loader: fn(pageOfItems) },
    play: async (context) => {
        const { args, canvas, step } = context;
        await scrollUntilAllLoaded(context);
        await step("See the all-loaded footer in place of the count and Load More", async () => {
            await expect(canvas.getByText("- All datasets loaded -")).toBeVisible();
            await expect(canvas.queryByText(/^Loaded \d+/)).not.toBeInTheDocument();
            await expect(loadMoreButton(context)).not.toBeInTheDocument();
            await expect(args.loader).toHaveBeenCalledTimes(ITEMS.length / PAGE_SIZE);
        });
    },

    // TODO a11y: aria-required-children, scrollable-region-focusable (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** With `showCountInFooter`, the all-loaded footer counts the items. */
export const CountsEveryPageOnceLoaded: Story = {
    args: { ...CountInFooter.args, loader: fn(pageOfItems) },
    play: async (context) => {
        const { canvas, step } = context;
        await scrollUntilAllLoaded(context);
        await step("See the footer count all 50 datasets in place of Load More", async () => {
            await expect(canvas.getByText("- 50 datasets loaded -")).toBeVisible();
            await expect(loadMoreButton(context)).not.toBeInTheDocument();
        });
    },

    // TODO a11y: aria-required-children, scrollable-region-focusable (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** An item the store adds outside the loader shows at once and counts toward the total. */
export const CountsItemAddedOutsideLoader: Story = {
    ...StoreOwnedItems,
    args: { ...StoreOwnedItems.args, fetchPage: fn(pageOfItems) },
    play: async (context) => {
        const { args, canvas, step, userEvent } = context;
        let loaded = 0;
        await step("See the list fill its height from the store, counting the rows out of 50", async () => {
            await waitUntilFilled(context);
            loaded = rowNames(context).length;
            await expect(rowNames(context)).toEqual(firstNames(loaded));
            await expectLoadedCount(context, loaded, ITEMS.length);
            await expect(args.fetchPage).toHaveBeenCalledTimes(loaded / PAGE_SIZE);
        });
        await step("Add an item; it shows at the end and the total counts it, with nothing fetched", async () => {
            await userEvent.click(canvas.getByRole("button", { name: "Add item" }));
            await waitFor(() => expect(rowNames(context)).toEqual([...firstNames(loaded), "Added dataset 1"]));
            await expectLoadedCount(context, loaded + 1, ITEMS.length + 1);
            await expect(args.fetchPage).toHaveBeenCalledTimes(loaded / PAGE_SIZE);
        });
        await step("Scroll to the end; the next page loads and the total still counts the added item", async () => {
            scrollToEnd(context);
            await waitFor(() => expect(rowNames(context)).toHaveLength(loaded + 1 + PAGE_SIZE));
            await expectLoadedCount(context, loaded + 1 + PAGE_SIZE, ITEMS.length + 1);
            await expect(args.fetchPage).toHaveBeenCalledTimes(loaded / PAGE_SIZE + 1);
        });
    },

    // TODO a11y: aria-required-children, button-name, scrollable-region-focusable (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};
