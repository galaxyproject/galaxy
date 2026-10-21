import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, fn, waitFor, within } from "storybook/test";
import { h } from "vue";

import GDropdown from "./GDropdown.vue";
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

/** An action item closes the real enclosing menu after it is selected. */
export const ChoosesActionAndClosesMenu: Story = {
    render:
        ({ label, ...props }) =>
        () =>
            h(GDropdown, { text: "Workflow actions" }, () => h(GDropdownItem, props, () => label)),
    play: async ({ canvas, userEvent, step }) => {
        await step("Open the workflow actions menu", async () => {
            const toggle = canvas.getByRole("button", { name: "Workflow actions" });
            await expect(toggle).toBeVisible();
            await expect(canvas.queryByRole("menu", { name: "Workflow actions" })).not.toBeInTheDocument();
            await userEvent.click(toggle);
            const menu = await canvas.findByRole("menu", { name: "Workflow actions" });
            await expect(menu).toBeVisible();
            await expect(within(menu).getByRole("menuitem", { name: "Copy workflow" })).toBeVisible();
        });
        await step("Choose an action and close its menu", async () => {
            const menu = canvas.getByRole("menu", { name: "Workflow actions" });
            await userEvent.click(within(menu).getByRole("menuitem", { name: "Copy workflow" }));
            await waitFor(() =>
                expect(canvas.queryByRole("menu", { name: "Workflow actions" })).not.toBeInTheDocument(),
            );
            await expect(canvas.getByRole("button", { name: "Workflow actions" })).toHaveAttribute(
                "aria-expanded",
                "false",
            );
        });
    },
};
