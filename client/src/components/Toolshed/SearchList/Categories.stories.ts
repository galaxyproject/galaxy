import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeRegisteredUser } from "@tests/test-data";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { exactly } from "@tests/test-data/text";
import { deferred } from "@tests/vitest/deferred";
import { expect, waitFor, within } from "storybook/test";
import { h, onBeforeUnmount, ref } from "vue";

import { TOOL_SHED_CATEGORIES, TOOL_SHED_URLS, toolShedCategories } from "../test_fixtures";

import Categories from "./Categories.vue";

let pendingCategories: ReturnType<typeof deferred<void>> | undefined;

const meta = {
    title: "Toolshed/SearchList/Categories",
    component: Categories,
    decorators: [withCurrentUser(() => getFakeRegisteredUser({ is_admin: true }))],
    args: { toolshedUrl: TOOL_SHED_URLS[0]!, loading: false },
    // The containing search page owns the loading flag while Categories fetches its rows.
    render: (args) => ({
        setup() {
            const loading = ref(args.loading);
            return () =>
                h(Categories, {
                    ...args,
                    loading: loading.value,
                    onOnLoading: (value: boolean) => {
                        loading.value = value;
                    },
                });
        },
    }),
    afterEach: async ({ canvasElement, args }) => {
        await waitFor(
            () => {
                const canvas = within(canvasElement);
                if (args.loading) {
                    expect(canvas.getByText(/^Loading categories\.\.\./)).toBeVisible();
                } else {
                    expect(canvas.getByText(TOOL_SHED_CATEGORIES[0]!.name)).toBeVisible();
                }
            },
            { timeout: 5000 },
        );
    },
    parameters: {
        msw: { handlers: { categories: toolShedCategories() } },
    },
} satisfies Meta<typeof Categories>;
export default meta;
type Story = StoryObj<typeof meta>;

export const AvailableCategories: Story = {
    play: async ({ canvasElement, step }) => {
        await step("Read each category, description and repository count", async () => {
            await expectCategories(canvasElement, ["Sequence Analysis", "Visualization"]);
        });
    },
};

/** The main Tool Shed is still replying to the administrator's category request. */
export const LoadingCategories: Story = {
    args: { loading: true },
    decorators: [
        (story) => ({
            setup() {
                const request = deferred<void>();
                pendingCategories = request;
                onBeforeUnmount(() => {
                    request.resolve();
                    if (pendingCategories === request) {
                        pendingCategories = undefined;
                    }
                });
                return () => h(story());
            },
        }),
    ],
    parameters: {
        msw: {
            handlers: {
                categories: toolShedCategories(
                    TOOL_SHED_CATEGORIES,
                    () => pendingCategories?.promise ?? Promise.resolve(),
                ),
            },
        },
    },
};

/** Read the complete rows by their visible cells, using the Tool Shed's integer repository counts. */
async function expectCategories(canvasElement: HTMLElement, names: string[]) {
    const table = await within(canvasElement).findByRole("table", {}, { timeout: 5000 });
    await waitFor(
        async () => {
            const rows = within(table).getAllByRole("row");
            expect(rows).toHaveLength(names.length + 1);
            for (const [index, name] of names.entries()) {
                const category = TOOL_SHED_CATEGORIES.find((entry) => entry.name === name)!;
                const cells = within(rows[index + 1]!).getAllByRole("cell");
                expect(cells).toHaveLength(3);
                await expect(within(cells[0]!).getByText(name, { exact: true })).toBeVisible();
                await expect(cells[1]!).toHaveTextContent(exactly(category.description));
                await expect(cells[2]!).toHaveTextContent(exactly(String(category.repositories)));
            }
        },
        { timeout: 5000 },
    );
    return table;
}

/** Order categories by repository count, then alphabetically, in both directions. */
export const SortsCategories: Story = {
    play: async ({ canvasElement, userEvent, step }) => {
        const table = await expectCategories(canvasElement, ["Sequence Analysis", "Visualization"]);
        const columns = within(table);
        await step("Sort repository counts from smallest to largest and back", async () => {
            const repositories = columns.getByRole("columnheader", { name: "Repositories" });
            await userEvent.click(repositories);
            await expectCategories(canvasElement, ["Visualization", "Sequence Analysis"]);
            await expect(repositories).toHaveAttribute("aria-sort", "ascending");
            await userEvent.click(repositories);
            await expectCategories(canvasElement, ["Sequence Analysis", "Visualization"]);
            await expect(repositories).toHaveAttribute("aria-sort", "descending");
        });
        await step("Sort category names alphabetically and in reverse", async () => {
            const category = columns.getByRole("columnheader", { name: "Category" });
            await userEvent.click(category);
            await expectCategories(canvasElement, ["Sequence Analysis", "Visualization"]);
            await expect(category).toHaveAttribute("aria-sort", "ascending");
            await userEvent.click(category);
            await expectCategories(canvasElement, ["Visualization", "Sequence Analysis"]);
            await expect(category).toHaveAttribute("aria-sort", "descending");
        });
    },
};
