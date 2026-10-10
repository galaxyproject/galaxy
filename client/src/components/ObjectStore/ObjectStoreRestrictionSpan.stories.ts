import type { Meta, StoryObj } from "@storybook/vue3-vite";

import ObjectStoreRestrictionSpan from "./ObjectStoreRestrictionSpan.vue";

const meta = {
    title: "ObjectStore/ObjectStoreRestrictionSpan",
    component: ObjectStoreRestrictionSpan,
} satisfies Meta<typeof ObjectStoreRestrictionSpan>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Storage restricted to one user: its datasets can't be shared, published or added to libraries. */
export const Private: Story = { args: { isPrivate: true } };

/** Storage that allows Galaxy's usual sharing, publishing and library features. */
export const Sharable: Story = { args: { isPrivate: false } };
