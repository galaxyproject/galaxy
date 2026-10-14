import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withModel } from "@tests/test-data/withModel";
import { expect, waitFor } from "storybook/test";
import { h } from "vue";

import DelayedInput from "./DelayedInput.vue";

export const DelayedInputWithModel = withModel(DelayedInput, "DelayedInputWithModel");

const meta = {
    title: "Common/DelayedInput",
    component: DelayedInput,
    excludeStories: ["DelayedInputWithModel"],
    render: (args) => () => h(DelayedInputWithModel, args),
    args: { value: "fastp", placeholder: "search tools", delay: 200 },
} satisfies Meta<typeof DelayedInput>;

export default meta;
type Story = StoryObj<typeof meta>;

/** The tool panel has a query ready to edit or clear. The parent reflects emitted values back into the input. */
export const WithQuery: Story = {};

/** While tool search is pending, the clear button displays a spinner. */
export const Searching: Story = {
    args: { loading: true },
};

/** Clear the tool query and keep the search field ready for another query. */
export const ClearsSearch: Story = {
    play: async ({ canvas, userEvent, step }) => {
        await step("Start with the existing tool query", async () => {
            const input = await canvas.findByRole("textbox");
            await expect(input).toBeVisible();
            await expect(input).toHaveValue("fastp");
        });
        await step("Clear the query and return focus to the search field", async () => {
            const input = canvas.getByRole("textbox");
            await userEvent.click(canvas.getByRole("button", { name: "Clear Search (esc)" }));
            await waitFor(() => expect(canvas.getByRole("textbox")).toHaveValue(""));
            await expect(canvas.getByRole("textbox")).toBeVisible();
            await expect(input).toHaveFocus();
        });
    },
};
