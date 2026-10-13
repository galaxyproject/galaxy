import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeHistorySummaryExtended } from "@tests/test-data";
import { getFakeFileSource } from "@tests/test-data/fileSources";
import { expect, waitFor, within } from "storybook/test";

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
    afterEach: async ({ canvasElement, args }) => {
        await waitFor(
            () =>
                expect(
                    within(canvasElement).getByRole("button", {
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
