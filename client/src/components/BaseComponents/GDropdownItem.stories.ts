import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { fn } from "storybook/test";
import { h } from "vue";

import GDropdownItem from "./GDropdownItem.vue";

type Args = InstanceType<typeof GDropdownItem>["$props"] & { label: string };

const meta = {
    title: "BaseComponents/GDropdownItem",
    component: GDropdownItem,
    args: { label: "Copy workflow", onClick: fn() },
    render:
        ({ label, ...props }) =>
        () =>
            h(GDropdownItem, props, () => label),
} satisfies Meta<Args>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Action: Story = {};

export const ExternalDownload: Story = {
    args: { label: "Download workflow", href: "https://example.org/workflow.ga", target: "_blank" },
};

export const DisabledDownload: Story = {
    args: { label: "Download unavailable", href: "https://example.org/workflow.ga", disabled: true },
};
