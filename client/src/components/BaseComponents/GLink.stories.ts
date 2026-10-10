import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { defineComponent, h, ref } from "vue";

import GLink from "./GLink.vue";

type GLinkArgs = InstanceType<typeof GLink>["$props"] & { label: string };

/**
 * A row that reacts to clicks, as history items and cards do, with a link inside it.
 * The count shows which link clicks reach the row.
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
                    h(GLink, attrs, slots),
                ],
            );
    },
});

const meta = {
    title: "BaseComponents/GLink",
    component: GLink,
    excludeStories: ["ClickableRow"],
    args: { label: "Show details" },
    render:
        ({ label, ...props }) =>
        () =>
            h(GLink, props, () => label),
} satisfies Meta<GLinkArgs>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Inline text that acts as a button, with no place to go. */
export const InlineButton: Story = {};

/** A link to another page in Galaxy, with a styled tooltip instead of the native title. */
export const InternalLink: Story = {
    args: { to: "/pages/create", label: "Create a page", title: "Create a new page", tooltip: true },
};

/** A link to a URL outside the router, rendered as a plain anchor. */
export const ExternalLink: Story = {
    args: { href: "https://example.org/data.txt", label: "data.txt" },
};

/** Unavailable: greyed out, no href to follow, clicks go nowhere, and the title says why. */
export const Disabled: Story = {
    args: {
        href: "https://example.org/data.txt",
        label: "data.txt",
        title: "Download data.txt",
        disabled: true,
        disabledTitle: "The upload hasn't finished yet",
    },
};

/** A link inside a clickable row: its clicks reach the row only while it's enabled. */
export const InClickableRow: Story = {
    args: { href: "https://example.org/data.txt", label: "data.txt" },
    render:
        ({ label, ...props }) =>
        () =>
            h(ClickableRow, props, () => label),
};
