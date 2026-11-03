import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeHistorySummaryExtended } from "@tests/test-data";
import { getFakeFileSource } from "@tests/test-data/fileSources";
import { expect, userEvent, waitFor, within } from "storybook/test";

import type { components } from "@/api";
import { http } from "@/api/client/__mocks__/http";
import type { BrowsableFilesSourcePlugin } from "@/api/remoteFiles";
import { TOOLBOX_USER, toolBoxState, withToolBoxState } from "@/components/Panels/test_fixtures";
import { CURRENT_HISTORY } from "@/components/SelectionField/test_fixtures";

import HistoryImport from "./HistoryImport.vue";

const ftp = getFakeFileSource({
    id: "_ftp",
    type: "gxftp",
    uri_root: "gxftp://",
    label: "FTP Directory",
    doc: "Galaxy User's FTP Directory",
    writable: false,
});

const importedHistory = getFakeHistorySummaryExtended({
    id: "9ac83716c25f084e",
    name: "History for Workflow Import",
    url: "/api/histories/9ac83716c25f084e",
    user_id: TOOLBOX_USER.id,
});
const currentHistory = getFakeHistorySummaryExtended({ ...CURRENT_HISTORY, user_id: TOOLBOX_USER.id });
const currentHistoryJobId = "b8a3fb13e55e4590";
const historyArchiveUrl = "https://usegalaxy.org/api/histories/exported_history/exports/archive.tar.gz";
const invocationArchiveUrl = "https://usegalaxy.org/api/invocations/exported_invocation/exports/archive.tar.gz";

const importJob = {
    id: "b8a3fb13e55e4589",
    model_class: "Job",
    tool_id: "__IMPORT_HISTORY__",
    history_id: importedHistory.id,
    state: "new",
    create_time: "2026-10-01T12:00:00",
    update_time: "2026-10-01T12:00:01",
} satisfies components["schemas"]["JobBaseModel"];

function fileSources(plugins: BrowsableFilesSourcePlugin[]) {
    return {
        msw: {
            handlers: {
                fileSources: http.get("/api/remote_files/plugins", ({ response }) => response(200).json(plugins)),
            },
        },
    };
}

interface HistoryImportStoryState {
    historyImportCompletes?: boolean;
}

function completedImport(): HistoryImportStoryState {
    return { historyImportCompletes: true };
}

const meta = {
    title: "HistoryImport",
    component: HistoryImport,
    decorators: [withToolBoxState],
    args: { invocationImport: false },
    parameters: {
        ...toolBoxState({ tools: [], toolSections: { default: {} } }),
        msw: {
            handlers: {
                ...fileSources([ftp]).msw.handlers,
                repository: http.get("/api/remote_files", ({ response }) =>
                    response(200).json([], { headers: { total_matches: "0" } }),
                ),
                templates: http.get("/api/file_source_templates", ({ response }) => response(200).json([])),
                importHistory: http.post("/api/histories", async ({ request, response }) => {
                    const form = await request.formData();
                    const source = form.get("archive_source") || "uploaded archive";
                    const job: components["schemas"]["JobImportHistoryResponse"] = {
                        ...importJob,
                        ...(form.get("name") ? {} : { id: currentHistoryJobId, history_id: currentHistory.id }),
                        message: `Importing history from source '${source}'. This history will be visible when the import is complete.`,
                    };
                    return response(200).json(job);
                }),
                history: http.get("/api/histories/{history_id}", ({ params, response }) =>
                    response(200).json(params.history_id === currentHistory.id ? currentHistory : importedHistory),
                ),
                job: http.get("/api/jobs/{job_id}", ({ params, response }) =>
                    response(200).json({
                        ...importJob,
                        ...(params.job_id === currentHistoryJobId
                            ? { id: currentHistoryJobId, history_id: currentHistory.id }
                            : {}),
                        state: "ok",
                        inputs: {},
                        outputs: {},
                        output_collections: {},
                        params: {},
                    }),
                ),
            },
        },
    },
    afterEach: async ({ canvasElement, args, parameters }) => {
        const state = parameters as HistoryImportStoryState;
        await waitFor(
            () =>
                expect(
                    state.historyImportCompletes
                        ? within(canvasElement).getByText("Done!", { exact: true })
                        : within(canvasElement).getByRole("button", {
                              name: args.invocationImport ? "Import invocation" : "Import history",
                          }),
                ).toBeVisible(),
            { timeout: 5000 },
        );
    },
} satisfies Meta<typeof HistoryImport>;
export default meta;
type Story = StoryObj<typeof meta>;

/** Import an archive URL, upload a local archive, or browse the account's FTP directory. */
export const HistoryWithRepository: Story = {};

/** An instance without a configured file source offers URL and local-file imports. */
export const HistoryWithoutRepository: Story = { parameters: fileSources([]) };

/** Workflow invocation archives can be imported into the current history or a new one. */
export const InvocationWithRepository: Story = { args: { invocationImport: true } };

export const ReplacesPublishedHistoryUrlWithArchive: Story = {
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        await canvas.findByRole("button", { name: "Import history" }, { timeout: 5000 });
        const input = canvas.getByRole("textbox");
        await step("Explain why a published-history URL is not an archive", async () => {
            await userEvent.type(input, "https://usegalaxy.org/u/some_user/h/exported_history");
            const warning = await canvas.findByRole("alert");
            expect(warning).toHaveTextContent(
                "It looks like you are trying to import a published history from another galaxy instance. You can only import histories via an archive URL.",
            );
            expect(within(warning).getByRole("link", { name: /Read more on the GTN/ })).toBeVisible();
        });
        await step("Replace it with an archive URL", async () => {
            await userEvent.clear(input);
            await userEvent.type(input, historyArchiveUrl);
            await waitFor(() => {
                expect(input).toHaveValue(historyArchiveUrl);
                expect(canvas.getByRole("button", { name: "Import history" })).not.toHaveAttribute(
                    "aria-disabled",
                    "true",
                );
                expect(canvas.queryByRole("alert")).not.toBeInTheDocument();
            });
        });
    },
};

export const ImportsArchiveIntoNewHistory: Story = {
    parameters: completedImport(),
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        const submit = await canvas.findByRole("button", { name: "Import history" }, { timeout: 5000 });
        await step("Import the history archive", async () => {
            await userEvent.type(canvas.getByRole("textbox"), historyArchiveUrl);
            expect(submit).not.toHaveAttribute("aria-disabled", "true");
            await userEvent.click(submit);
        });
        await step("Show the imported history after its real job response completes", async () => {
            await canvas.findByText("Done!", { exact: true }, { timeout: 5000 });
            expect(await canvas.findByText("History for Workflow Import", { exact: true })).toBeVisible();
            expect(canvas.getByRole("link", { name: "your histories" })).toBeVisible();
            expect(canvas.getByRole("link", { name: "your histories" })).toHaveAttribute("href", "/histories/list");
            expect(canvas.queryByRole("button", { name: "Import history" })).not.toBeInTheDocument();
        });
    },
};

export const ImportsInvocationIntoCurrentHistory: Story = {
    ...InvocationWithRepository,
    parameters: completedImport(),
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        const submit = await canvas.findByRole("button", { name: "Import invocation" }, { timeout: 5000 });
        await step("Choose the current history for the invocation archive", async () => {
            await userEvent.click(canvas.getByRole("radio", { name: "Import into the current history." }));
            expect(canvas.getByRole("radio", { name: "Import into the current history." })).toBeChecked();
            expect(canvas.getByRole("radio", { name: "Import into a new history." })).not.toBeChecked();
            await userEvent.type(canvas.getByRole("textbox"), invocationArchiveUrl);
            expect(submit).not.toHaveAttribute("aria-disabled", "true");
            await userEvent.click(submit);
        });
        await step("Show the invocation's target history after import", async () => {
            await canvas.findByText("Done!", { exact: true }, { timeout: 5000 });
            expect(await canvas.findByText("RNA-seq run", { exact: true })).toBeVisible();
            expect(canvas.queryByText("History for Workflow Import", { exact: true })).not.toBeInTheDocument();
            expect(canvas.getByRole("link", { name: "your invocations" })).toBeVisible();
            expect(canvas.getByRole("link", { name: "your invocations" })).toHaveAttribute(
                "href",
                "/workflows/invocations",
            );
            expect(canvas.queryByRole("button", { name: "Import invocation" })).not.toBeInTheDocument();
        });
    },
};
