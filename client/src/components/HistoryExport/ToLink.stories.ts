import type { Decorator, Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, within } from "storybook/test";
import { h } from "vue";

import { http } from "@/api/client/__mocks__/http";
import type { JobExportHistoryArchiveModel } from "@/api/histories.export";

import { EXPORT_JOB_ID, EXPORTED_HISTORY_ID, exportJobHandler } from "./test_fixtures";

import ToLink from "./ToLink.vue";

const EXPORT_ID = "a5f9d7e7b8c41b2e";
const QUALIFIED_EXPORTS_URL = `https://usegalaxy.org/api/histories/${EXPORTED_HISTORY_ID}/exports`;
const PERMANENT_URL = `${QUALIFIED_EXPORTS_URL}/${EXPORT_ID}`;

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
        external_download_permanent_url: PERMANENT_URL,
    };
}

/** The history's archive record once its export job stopped without writing the archive. */
function failedExport(): JobExportHistoryArchiveModel {
    return { ...historyExport(false), preparing: false };
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
    // The job polls a second later; let it finish here rather than in the next story. The play
    // waits for this too; this covers the story rendered without its play.
    afterEach: async ({ canvasElement }) => {
        await expect(
            await within(canvasElement).findByText(/Link for download ready/, {}, { timeout: 5000 }),
        ).toBeVisible();
    },
    play: async ({ canvas, step }) => {
        await step("See Galaxy preparing the archive", async () => {
            // The message ends in a full stop and the spinner appends "...", so it shows four dots;
            // accept three too, so dropping the stray full stop doesn't fail this.
            const preparing = await canvas.findByText(
                /^Galaxy server is preparing history for download, this will likely take a while\.{3,4}$/,
                {},
                { timeout: 5000 },
            );
            await expect(preparing).toBeVisible();
            await expect(canvas.getByTitle("loading")).toBeVisible();
        });
        await step("Once the job finishes, see the archive's permanent link and that archives expire", async () => {
            await expect(await canvas.findByText("Link for download ready", {}, { timeout: 5000 })).toBeVisible();
            await expect(canvas.queryByText(/preparing history for download/)).not.toBeInTheDocument();
            const link = canvas.getByRole("link", { name: PERMANENT_URL });
            await expect(link).toHaveAttribute("href", PERMANENT_URL);
            await expect(
                canvas.getByText(/^Use this link to download the archive or import it on another Galaxy server\.$/),
            ).toBeVisible();
            await expect(canvas.getByRole("alert")).toHaveTextContent(
                /^History archives are removed at regular intervals\. For permanent storage download the archive, export to a repository or import the archive on another Galaxy server\.$/,
            );
        });
    },
};

/** Sees that no archive is ready since `situation`, the page saying `why`, and a link to start one. */
function offersNewArchive(situation: string, why: string): Story["play"] {
    return async ({ canvas, step }) => {
        await step(`See that no archive is ready since ${situation}, with a link to start one`, async () => {
            const reason = await canvas.findByText(`No link for history export ready, ${why}.`, {}, { timeout: 5000 });
            await expect(reason).toBeVisible();
            await expect(
                canvas.getByRole("link", { name: "Click here to generate a new archive for this history." }),
            ).toBeVisible();
            await expect(canvas.queryByText(/Loading history export information/)).not.toBeInTheDocument();
            await expect(canvas.queryByTitle("loading")).not.toBeInTheDocument();
            await expect(canvas.queryByText("Link for download ready")).not.toBeInTheDocument();
        });
    };
}

/** The history was never exported; the user can start the first archive. */
export const NoExports: Story = {
    parameters: { msw: { handlers: { exports: exports(() => []) } } },
    play: offersNewArchive("the history was never exported", "no history export ever initiated for this history"),
};

/** The history's last export stopped without writing an archive; the user can start another. */
export const PreviousExportFailed: Story = {
    parameters: { msw: { handlers: { exports: exports(() => [failedExport()]) } } },
    play: offersNewArchive("the last export failed", "previous history export archival likely failed"),
};
