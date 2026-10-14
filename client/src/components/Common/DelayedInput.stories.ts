import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withModel } from "@tests/test-data/withModel";
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
