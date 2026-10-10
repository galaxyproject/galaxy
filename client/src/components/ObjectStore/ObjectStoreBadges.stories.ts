import type { Meta, StoryObj } from "@storybook/vue3-vite";

import ObjectStoreBadges from "./ObjectStoreBadges.vue";

const meta = {
    title: "ObjectStore/ObjectStoreBadges",
    component: ObjectStoreBadges,
    args: {
        badges: [
            { type: "more_secure", message: "Encrypted at rest.", source: "admin" },
            { type: "slower", message: "Backed by tape; reads can take hours.", source: "admin" },
        ],
    },
} satisfies Meta<typeof ObjectStoreBadges>;

export default meta;
type Story = StoryObj<typeof meta>;

/** No size given, so each badge falls back to its default `lg` icon size. */
export const DefaultSize: Story = {};

/** Badges drawn at twice the base icon size. */
export const DoubleSize: Story = { args: { size: "2x" } };

export const NonInteractive: Story = { args: { interactive: false } };
