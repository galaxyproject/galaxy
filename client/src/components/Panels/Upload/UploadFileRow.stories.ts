import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeHistorySummary } from "@tests/test-data";
import { withCurrentHistory } from "@tests/test-data/currentHistory";
import { h } from "vue";

import { makeLocalFileItem, makeUrlItem, withUploadState } from "@/composables/upload/testHelpers/uploadFixtures";

import UploadFileRow from "./UploadFileRow.vue";

const HISTORY_ID = "c4f1a2b3d5e60718";
const HISTORY = getFakeHistorySummary({
    id: HISTORY_ID,
    name: "Mutation calling",
    url: `/api/histories/${HISTORY_ID}`,
});

/** One upload in the upload panel's queue, headed for the current history. */
const meta = {
    title: "Panels/Upload/UploadFileRow",
    component: UploadFileRow,
    decorators: [withCurrentHistory(HISTORY)],
    // Replaces the fixture's createdAt (0, i.e. 1970) with a minute before the story renders, so the elapsed time reads as it would in the app.
    render: (args) => () => h(UploadFileRow, { ...args, file: { ...args.file, createdAt: Date.now() - 60_000 } }),
} satisfies Meta<typeof UploadFileRow>;

export default meta;
type Story = StoryObj<typeof meta>;

/** A pasted link waits its turn; the row shows the link, with a copy button on hover. */
export const LinkQueued: Story = {
    args: {
        file: withUploadState(
            makeUrlItem({
                name: "mutant_R1.fastq",
                url: "https://zenodo.org/records/582600/files/mutant_R1.fastq",
                targetHistoryId: HISTORY_ID,
            }),
        ),
    },
};

/** A file from the user's computer, part way through; it has no link to show and can be cancelled. */
export const FileUploading: Story = {
    args: {
        file: withUploadState(
            makeLocalFileItem({
                name: "wildtype.fna",
                size: 4_700_000,
                fileData: new File([], "wildtype.fna"),
                targetHistoryId: HISTORY_ID,
            }),
            { status: "uploading", progress: 45 },
        ),
    },
};
