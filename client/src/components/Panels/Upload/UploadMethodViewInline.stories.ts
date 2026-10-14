import type { Meta, StoryObj } from "@storybook/vue3-vite";

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
