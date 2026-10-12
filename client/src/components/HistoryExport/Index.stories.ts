import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { getFakeFileSource } from "@tests/test-data/fileSources";
import { HttpResponse } from "msw";

import { http } from "@/api/client/__mocks__/http";

import Index from "./Index.vue";

const REPOSITORY = getFakeFileSource({
    id: "history-archives",
    label: "History archives",
    doc: "A directory for exported Galaxy histories.",
});

const meta = {
    title: "HistoryExport/Index",
    component: Index,
    decorators: [withCurrentUser()],
    args: { historyId: "test_id" },
    parameters: {
        msw: {
            handlers: {
                fileSources: http.get("/api/remote_files/plugins", ({ response }) => response(200).json([REPOSITORY])),
                templates: http.get("/api/file_source_templates", ({ response }) => response(200).json([])),
                // The repository is an empty directory; its root can still be selected as a destination.
                listing: http.get("/api/remote_files", ({ query, response }) => {
                    if (query.get("target") === REPOSITORY.uri_root) {
                        return response(200).json([], { headers: { total_matches: "0" } });
                    }
                }),
                exports: http.untyped.get("/api/histories/test_id/exports", () => HttpResponse.json([])),
            },
        },
    },
} satisfies Meta<typeof Index>;
export default meta;
type Story = StoryObj<typeof meta>;

/** A writable POSIX source offers both a download link and a repository export. This history has no archive yet. */
export const WritableRepository: Story = {};

/** Read-only sources cannot receive an archive: the download-link view is shown directly. */
export const LinkOnly: Story = {
    parameters: {
        msw: {
            handlers: {
                fileSources: http.get("/api/remote_files/plugins", ({ response }) =>
                    response(200).json([getFakeFileSource({ ...REPOSITORY, writable: false })]),
                ),
            },
        },
    },
};
