import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { defineComponent, h, ref } from "vue";

import GButton from "./GButton.vue";

type GButtonArgs = InstanceType<typeof GButton>["$props"] & { label: string };

/**
 * A row that reacts to clicks, as history items and cards do, with a button inside it.
 * The count shows which button clicks reach the row.
 */
export const ClickableRow = defineComponent({
    name: "ClickableRow",
    inheritAttrs: false,
    setup(_, { attrs, slots }) {
        const rowClicks = ref(0);

        function onRowClick() {
            rowClicks.value++;
        }

        return () =>
            h(
                "div",
                {
                    "data-description": "clickable row",
                    style: "display: flex; gap: 1rem; align-items: center; padding: 0.5rem; border: 1px solid var(--color-grey-300); cursor: pointer",
                    onClick: onRowClick,
                },
                [
                    h("span", { "data-description": "row clicks" }, `Row clicks: ${rowClicks.value}`),
                    h(GButton, attrs, slots),
                ],
            );
    },
});

const meta = {
    title: "BaseComponents/GButton",
    component: GButton,
    excludeStories: ["ClickableRow"],
    args: { label: "Save", title: "Save your changes" },
    render:
        ({ label, ...props }) =>
        () =>
            h(GButton, props, () => label),
} satisfies Meta<GButtonArgs>;

export default meta;
type Story = StoryObj<typeof meta>;

/** A plain grey button with a native title. */
export const Default: Story = {};

/** Unavailable, with a title that says why. It still takes hover so the title can show. */
export const Disabled: Story = { args: { disabled: true, disabledTitle: "Nothing to save yet" } };

/** Working: a spinner, and clicks are ignored, but the button keeps its colour. */
export const Loading: Story = { args: { loading: true, label: "Saving" } };

/** A link to another page in Galaxy, with a styled tooltip instead of the native title. */
export const InternalLink: Story = {
    args: { to: "/pages/create", label: "Create page", title: "Create a new page", tooltip: true },
};

/** A link to a URL outside the router, rendered as a plain anchor. */
export const ExternalLink: Story = {
    args: { href: "https://example.org/data.txt", label: "Download", title: "Download the data" },
};

/** A button inside a clickable row: its clicks reach the row only while it's enabled. */
export const InClickableRow: Story = {
    args: { label: "Delete", title: "Delete this item" },
    render:
        ({ label, ...props }) =>
        () =>
            h(ClickableRow, props, () => label),
};
