import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect } from "storybook/test";

import { uploadMethodHandlers } from "./test_fixtures";

import UploadMethodViewInline from "./UploadMethodViewInline.vue";

const HISTORY_ID = "f2db41e1fa331b3e";

/**
 * The upload pane embedded in another page: the dataset methods down the side, the
 * selected one beside them, and Cancel and Start below.
 */
const meta = {
    title: "Panels/Upload/UploadMethodViewInline",
    component: UploadMethodViewInline,
    parameters: { msw: { handlers: uploadMethodHandlers } },
} satisfies Meta<typeof UploadMethodViewInline>;

export default meta;
type Story = StoryObj<typeof meta>;

/** A collection creator's "Upload" tab, for paired reads: no tips, and uploads can't become collections here. */
export const CollectionCreatorUpload: Story = {
    args: {
        config: { allowCollections: false, formats: ["fastqsanger", "fastqsanger.gz"], targetHistoryId: HISTORY_ID },
    },
};

/** The upload dialog, as `useUploadMethodModal` opens it by default: the selected method's tips are shown. */
export const WithTips: Story = {
    args: {
        config: { allowCollections: false, multiple: true, targetHistoryId: HISTORY_ID },
        hideTips: false,
    },
};

/** Switching the upload method replaces the editor beside the method cards. */
export const SwitchesUploadMethod: Story = {
    args: CollectionCreatorUpload.args,
    play: async ({ canvas, userEvent, step }) => {
        await step("Starts with the computer upload editor", async () => {
            await expect(
                canvas.findByRole("button", { name: "Browse Files" }, { timeout: 5000 }),
            ).resolves.toBeVisible();
            await expect(canvas.getByText("Drag files here")).toBeVisible();
            await expect(canvas.queryByRole("textbox", { name: /Paste data for/ })).not.toBeInTheDocument();
        });
        await step("Choose pasted content and see its editor", async () => {
            await userEvent.click(canvas.getByRole("button", { name: /Paste File Content/ }));
            await expect(
                canvas.findByRole("textbox", { name: /Paste data for/ }, { timeout: 5000 }),
            ).resolves.toBeVisible();
            await expect(canvas.queryByRole("button", { name: "Browse Files" })).not.toBeInTheDocument();
            await expect(canvas.queryByText("Drag files here")).not.toBeInTheDocument();
        });
        await step("Return to the computer upload editor", async () => {
            await userEvent.click(canvas.getByRole("button", { name: /Upload from Computer/ }));
            await expect(
                canvas.findByRole("button", { name: "Browse Files" }, { timeout: 5000 }),
            ).resolves.toBeVisible();
            await expect(canvas.getByText("Drag files here")).toBeVisible();
            await expect(canvas.queryByRole("textbox", { name: /Paste data for/ })).not.toBeInTheDocument();
        });
    },
};
