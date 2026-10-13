import type { Meta, StoryObj } from "@storybook/vue3-vite";

import TextSummary from "./TextSummary.vue";

const meta = {
    title: "Common/TextSummary",
    component: TextSummary,
    args: {
        description: "Trimmed <b>paired</b> reads",
    },
} satisfies Meta<typeof TextSummary>;

export default meta;
type Story = StoryObj<typeof meta>;

/** A history annotation: markup in it shows as literal text. */
export const PlainText: Story = {};

/** A workflow annotation, which callers opt into rendering as sanitized HTML. */
export const RenderedHtml: Story = {
    args: { isHtml: true },
};
