import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, waitFor } from "storybook/test";
import { defineComponent, h, ref } from "vue";

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

const EXPLANATION = "Select the dataset containing your paired-end reads.";

/** Reveal the configured heading and complete explanation. */
export const ReadsTitle: Story = {
    play: async ({ canvas, userEvent, step }) => {
        await step("Open the input explanation and read its title", async () => {
            const explanation = canvas.getByText(EXPLANATION, { exact: true });
            await expect(explanation).toBeInTheDocument();
            await expect(explanation).not.toBeVisible();
            await userEvent.click(canvas.getByRole("button", { name: "About this input" }));
            await expect(explanation).toBeVisible();
            await expect(canvas.getByText("Workflow input", { exact: true })).toBeVisible();
        });
    },
};

/** Open details and dismiss them with the close icon beside the heading. */
export const ClosesDetails: Story = {
    play: async ({ canvas, userEvent, step }) => {
        await step("Open and close the explanation", async () => {
            const explanation = canvas.getByText(EXPLANATION, { exact: true });
            await expect(explanation).not.toBeVisible();
            await userEvent.click(canvas.getByRole("button", { name: "About this input" }));
            await expect(explanation).toBeVisible();
            // The close icon has no accessible name; it sits immediately beside the visible title.
            await userEvent.click(canvas.getByText("Workflow input", { exact: true }).nextElementSibling!);
            await waitFor(() => expect(explanation).not.toBeVisible());
        });
    },
};

/** Clicking elsewhere in the document dismisses the explanation. */
export const ClicksOutside: Story = {
    play: async ({ canvas, userEvent, step }) => {
        await step("Dismiss details by clicking outside", async () => {
            const explanation = canvas.getByText(EXPLANATION, { exact: true });
            await expect(explanation).not.toBeVisible();
            await userEvent.click(canvas.getByRole("button", { name: "About this input" }));
            await expect(explanation).toBeVisible();
            await userEvent.click(document.body);
            await waitFor(() => expect(explanation).not.toBeVisible());
        });
    },
};

/** Disable an open explanation through a control inside it. */
export const DisablesOpenDetails: Story = {
    render: (args) => ({
        setup() {
            const disabled = ref(false);
            return () =>
                h(
                    Popper,
                    { ...args, disabled: disabled.value },
                    {
                        reference: () => h("button", { type: "button" }, "About this input"),
                        default: () => [
                            h("p", EXPLANATION),
                            h(
                                "button",
                                {
                                    type: "button",
                                    onClick: () => {
                                        disabled.value = true;
                                    },
                                },
                                "Disable explanation",
                            ),
                        ],
                    },
                );
        },
    }),
    play: async ({ canvas, userEvent, step }) => {
        await step("Disable details while they are open", async () => {
            const explanation = canvas.getByText(EXPLANATION, { exact: true });
            await expect(explanation).not.toBeVisible();
            await userEvent.click(canvas.getByRole("button", { name: "About this input" }));
            await expect(explanation).toBeVisible();
            await userEvent.click(canvas.getByRole("button", { name: "Disable explanation" }));
            await waitFor(() => expect(explanation).not.toBeVisible());
        });
    },
};

/** Reading and clicking inside a click-triggered explanation keeps it open. */
export const ReadsInsideDetails: Story = {
    play: async ({ canvas, userEvent, step }) => {
        await step("Read and click within the open explanation", async () => {
            const explanation = canvas.getByText(EXPLANATION, { exact: true });
            await expect(explanation).not.toBeVisible();
            await userEvent.click(canvas.getByRole("button", { name: "About this input" }));
            await expect(explanation).toBeVisible();
            await userEvent.hover(explanation);
            await expect(explanation).toBeVisible();
            await userEvent.unhover(explanation);
            await expect(explanation).toBeVisible();
            await userEvent.click(explanation);
            await expect(explanation).toBeVisible();
        });
    },
};
