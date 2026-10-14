import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { defineComponent, h } from "vue";

import Popper from "./Popper.vue";

/** The input's label and explanation supplied by the surrounding form. */
export const InputPopover = defineComponent({
    name: "InputPopover",
    inheritAttrs: false,
    setup(_props, { attrs }) {
        return () =>
            h(Popper, attrs, {
                reference: () => h("button", { type: "button" }, "About this input"),
                default: () => h("p", { class: "p-2 mb-0" }, "Select the dataset containing your paired-end reads."),
            });
    },
});

const meta = {
    title: "Popper",
    component: Popper,
    excludeStories: ["InputPopover"],
    render: (args) => () => h(InputPopover, args),
    args: { title: "Workflow input", placement: "bottom", trigger: "click", interactive: false, mode: "dark" },
    // These options bind the Popper instance and its listeners once, when the component mounts.
    argTypes: {
        placement: { control: false },
        trigger: { control: false },
        interactive: { control: false },
        hoverDelay: { control: false },
    },
} satisfies Meta<typeof Popper>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Click the input's reference to open details; dismiss with the close icon, Escape, or an outside click. */
export const ClickDetails: Story = {};

/** A short explanation appears after the usual tooltip hover delay. */
export const HoverHelp: Story = {
    args: { trigger: "hover", mode: "light" },
};

/** Moving from the reference into the explanation keeps this hover popover open. */
export const InteractiveHelp: Story = {
    args: { trigger: "hover", interactive: true, mode: "light" },
};
