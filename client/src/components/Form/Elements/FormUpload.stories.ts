import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withModel } from "@tests/test-data/withModel";
import { h } from "vue";

import FormUpload from "./FormUpload.vue";

export const FormUploadWithModel = withModel(FormUpload, "FormUploadWithModel");
type Args = Omit<InstanceType<typeof FormUpload>["$props"], "value"> & { value: string | null };

const meta = {
    title: "Form/Elements/FormUpload",
    component: FormUpload,
    excludeStories: ["FormUploadWithModel"],
    render: (args) => () => h(FormUploadWithModel, args),
    args: { value: null },
} satisfies Meta<Args>;

export default meta;
type Story = StoryObj<Args>;

/** A tool form with an empty file-content parameter. */
export const NoFileChosen: Story = {};

/** Existing CSV parameter contents are previewed read-only beside the file picker. */
export const CsvContents: Story = {
    args: { value: "sample,condition,replicate\nsample_01,treated,1\nsample_02,control,1" },
};
