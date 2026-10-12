import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeRegisteredUser } from "@tests/test-data";
import { withCurrentUser } from "@tests/test-data/currentUser";
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

export const AvailableCategories: Story = {};

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
