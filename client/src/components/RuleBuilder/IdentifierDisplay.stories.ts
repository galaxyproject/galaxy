import type { Decorator, Meta, StoryObj } from "@storybook/vue3-vite";
import { fn } from "storybook/test";
import { h } from "vue";

import IdentifierDisplay from "./IdentifierDisplay.vue";

const withMappingList: Decorator = (story) => ({
    setup: () => () => h("ul", [h(story())]),
});

const meta = {
    title: "RuleBuilder/IdentifierDisplay",
    component: IdentifierDisplay,
    decorators: [withMappingList],
    args: {
        type: "list_identifiers",
        columns: [0],
        colHeaders: ["A", "B"],
        onMouseover: fn(),
        onMouseout: fn(),
    },
} satisfies Meta<typeof IdentifierDisplay>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Column A names the samples in a dataset collection. Hover events let the rule builder highlight that column. */
export const SampleIdentifiers: Story = {};

/** Two columns describe nested collection levels, such as condition and replicate. */
export const NestedIdentifiers: Story = {
    args: { columns: [0, 1] },
};
