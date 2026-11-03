import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withModel } from "@tests/test-data/withModel";
import { h } from "vue";

import FormText from "./FormText.vue";

export const FormTextWithModel = withModel(FormText, "FormTextWithModel");

/** `value` has no declared type, so its `""` default types it as a string; a multiple field holds a list. */
type Args = Omit<InstanceType<typeof FormText>["$props"], "value"> & { value?: string | string[] };

/** The free-text field of tool and workflow forms. */
const meta = {
    title: "Form/Elements/FormText",
    component: FormText,
    excludeStories: ["FormTextWithModel"],
    render: (args) => () => h(FormTextWithModel, args),
} satisfies Meta<Args>;

export default meta;
type Story = StoryObj<Args>;

export const Text: Story = { args: { id: "sample_name", value: "wild_type_rep1" } };

/** A saved secret in the user's preferences, which Galaxy sends as a placeholder rather than the token. */
export const Password: Story = {
    args: { id: "dropbox|access_token", type: "password", value: "__SECRET_PLACEHOLDER__" },
};

/**
 * A run form shows a column picker whose dataset comes from an earlier tool step as free text;
 * any type but password is a text box.
 */
export const WorkflowDataColumn: Story = { args: { id: "column", type: "data_column", value: "2" } };

/** A tool parameter declared with `area="true"`, such as an awk program. */
export const TextArea: Story = { args: { id: "code", area: true, value: '$1 == "chr1" { print $0 }' } };

/** A workflow text input that accepts several values shows one per line. */
export const MultipleValues: Story = {
    args: { id: "sample_names", multiple: true, value: ["wild_type_rep1", "wild_type_rep2", "knockout_rep1"] },
};

/** A text parameter with static options, as `TextToolParameter` sends them, suggests them while typing. */
export const WithSuggestions: Story = {
    args: {
        id: "adapter",
        datalist: [
            { label: "Illumina universal", value: "AGATCGGAAGAGC" },
            { label: "Nextera transposase", value: "CTGTCTCTTATA" },
            { label: "Illumina small RNA", value: "TGGAATTCTCGG" },
        ],
    },
};

/** A `${sample}` replacement parameter on the workflow run form, colored and marked with a thick left border. */
export const WorkflowParameter: Story = {
    args: { id: "sample", color: "hsl( 100, 70%, 30% )", cls: "ui-input-linked" },
};
