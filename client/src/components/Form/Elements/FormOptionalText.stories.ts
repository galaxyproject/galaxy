import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withModel } from "@tests/test-data/withModel";
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

export const WithValue: Story = { args: { value: "hg38" } };

/** A null value leaves the parameter unset: the switch is off and there is no text box. */
export const Unset: Story = { args: { value: null } };
