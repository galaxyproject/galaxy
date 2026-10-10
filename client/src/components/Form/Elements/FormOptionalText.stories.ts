import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withModel } from "@tests/test-data/withModel";
import { expect, userEvent } from "storybook/test";
import { h } from "vue";

import FormOptionalText from "./FormOptionalText.vue";

export const FormOptionalTextWithModel = withModel(FormOptionalText, "FormOptionalTextWithModel");

/** `value` has no declared type, so its `""` default types it as a string; an unset parameter is null. */
type Args = Omit<InstanceType<typeof FormOptionalText>["$props"], "value"> & { value?: string | null };

/**
 * Workflow forms show an optional select whose options aren't known yet, such as reference genomes
 * filtered by a connected dataset's build, as optional free text.
 */
const meta = {
    title: "Form/Elements/FormOptionalText",
    component: FormOptionalText,
    excludeStories: ["FormOptionalTextWithModel"],
    render: (args) => () => h(FormOptionalTextWithModel, args),
} satisfies Meta<Args>;

export default meta;
type Story = StoryObj<Args>;

type Canvas = Parameters<NonNullable<Story["play"]>>[0]["canvas"];

const SWITCH = "Set value for this optional select field?";

/**
 * Sees the text box showing `value` with the switch on, or no text box with the switch off. After a
 * click the browser has already flipped the switch, so the text box is what follows the app's state.
 */
async function seeValue(canvas: Canvas, value: string | null) {
    const toggle = canvas.getByRole("switch", { name: SWITCH });
    if (value === null) {
        await expect(canvas.queryByRole("textbox")).not.toBeInTheDocument();
        await expect(toggle).not.toBeChecked();
    } else {
        await expect(canvas.getByRole("textbox")).toHaveValue(value);
        await expect(toggle).toBeChecked();
    }
}

export const WithValue: Story = {
    args: { value: "hg38" },
    play: async ({ canvas, step }) => {
        await step('See the switch on and "hg38" in the text box', async () => {
            await seeValue(canvas, "hg38");
        });
    },

    // TODO a11y: label (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** A null value leaves the parameter unset: the switch is off and there is no text box. */
export const Unset: Story = {
    args: { value: null },
    play: async ({ canvas, step }) => {
        await step("See the switch off and no text box", async () => {
            await seeValue(canvas, null);
        });
    },
};

/** Switching off unsets the value; switching back on starts from an empty text box. */
export const SwitchesOffAndBackOn: Story = {
    args: { value: "hg38" },
    play: async ({ canvas, step }) => {
        await step('See the switch on with "hg38"', async () => {
            await seeValue(canvas, "hg38");
        });
        await step("Switch it off: the text box goes away", async () => {
            await userEvent.click(canvas.getByText(SWITCH));
            await seeValue(canvas, null);
        });
        await step("Switch it back on: the text box is empty", async () => {
            await userEvent.click(canvas.getByText(SWITCH));
            await seeValue(canvas, "");
        });
    },

    // TODO a11y: label (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};
