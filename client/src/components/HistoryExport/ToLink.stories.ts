import type { Decorator, Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, within } from "storybook/test";
import { h } from "vue";

import { http } from "@/api/client/__mocks__/http";
import type { JobExportHistoryArchiveModel } from "@/api/histories.export";

import { EXPORT_JOB_ID, EXPORTED_HISTORY_ID, exportJobHandler } from "./test_fixtures";

import ToLink from "./ToLink.vue";

const EXPORT_ID = "a5f9d7e7b8c41b2e";
const QUALIFIED_EXPORTS_URL = `https://usegalaxy.org/api/histories/${EXPORTED_HISTORY_ID}/exports`;

/** The history's archive record while its export job runs, or once it has finished. */
function historyExport(jobDone: boolean): JobExportHistoryArchiveModel {
    return {
        id: EXPORT_ID,
        job_id: EXPORT_JOB_ID,
        ready: jobDone,
        preparing: !jobDone,
        up_to_date: true,
        download_url: `/api/histories/${EXPORTED_HISTORY_ID}/exports/${EXPORT_ID}`,
        external_download_latest_url: `${QUALIFIED_EXPORTS_URL}/latest`,
        external_download_permanent_url: `${QUALIFIED_EXPORTS_URL}/${EXPORT_ID}`,
    };
}

function exports(records: () => JobExportHistoryArchiveModel[]) {
    return http.get("/api/histories/{history_id}/exports", ({ response }) => response(200).json(records()));
}

/** How many more polls see the export job running; each render starts it over. */
let runningPolls = 0;

const withExportJobStarted: Decorator = (story) => ({
    setup() {
        runningPolls = 1;
    },
    render: () => h(story()),
});

/** The link to a history's archive, from the history's export page. */
const meta = {
    title: "HistoryExport/ToLink",
    component: ToLink,
    args: { historyId: EXPORTED_HISTORY_ID },
} satisfies Meta<typeof ToLink>;

export default meta;
type Story = StoryObj<typeof meta>;

/** An archive is being written; the page waits on its job, then shows the download link. */
export const Preparing: Story = {
    decorators: [withExportJobStarted],
    parameters: {
        msw: {
            handlers: {
                exports: exports(() => [historyExport(runningPolls <= 0)]),
                job: exportJobHandler(() => (runningPolls-- > 0 ? "running" : "ok")),
                // The download link's job details look for an invocation that ran the job.
                invocations: http.get("/api/invocations", ({ response }) => response(200).json([])),
            },
        },
    },
    // The job polls a second later; let it finish here rather than in the next story.
    afterEach: async ({ canvasElement }) => {
        await expect(
            await within(canvasElement).findByText(/Link for download ready/, {}, { timeout: 5000 }),
        ).toBeVisible();
    },
};

/** The history was never exported; the user can start the first archive. */
export const NoExports: Story = {
    parameters: { msw: { handlers: { exports: exports(() => []) } } },
};
