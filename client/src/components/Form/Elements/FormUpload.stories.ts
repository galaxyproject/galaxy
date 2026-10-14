import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withModel } from "@tests/test-data/withModel";
import { expect } from "storybook/test";
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
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];
const CSV_CONTENTS = "sample,condition,replicate\nsample_01,treated,1\nsample_02,control,1";
const SPACED_CSV = "H1, H2, H3\nv1, v2, v3";

async function readCsvPreview({ canvas }: PlayContext, contents: string) {
    const preview = canvas.getByRole("textbox");
    await expect(preview).toBeVisible();
    await expect(preview).toHaveValue(contents);
    await expect(preview).toBeDisabled();
}

/** A tool form with an empty file-content parameter. */
export const NoFileChosen: Story = {
    play: async ({ canvas, step }) => {
        await step("Read the empty file picker without a visible content preview", async () => {
            await expect(canvas.getByText("No file chosen", { exact: true })).toBeVisible();
            await expect(canvas.queryByRole("textbox")).not.toBeInTheDocument();
        });
    },
};

/** Existing CSV parameter contents are previewed read-only beside the file picker. */
export const CsvContents: Story = {
    args: { value: CSV_CONTENTS },
    play: async (context) => {
        await context.step("Read the complete existing CSV contents in a disabled preview", async () => {
            await readCsvPreview(context, CSV_CONTENTS);
        });
    },
};

/** Spaces after delimiters and the row boundary remain exactly as supplied. */
export const SpacedCsvPreview: Story = {
    args: { value: SPACED_CSV },
    play: async (context) => {
        await context.step("Read spaced CSV contents verbatim in a disabled preview", async () => {
            await readCsvPreview(context, SPACED_CSV);
        });
    },
};
