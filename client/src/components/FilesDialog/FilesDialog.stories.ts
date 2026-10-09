import type { Meta, StoryObj } from "@storybook/vue3-vite";

import { configurationHandler, http } from "@/api/client/__mocks__/http";
import type { FileSourceTemplateSummary } from "@/api/fileSources";

/**
 * The remote file tree the API serves (gxfiles://pdb-gzip):
 *
 * |-- directory1
 * |   |-- directory1file1
 * |   |-- directory1file2
 * |   |-- directory1file3
 * |   |-- subdirectory1
 * |   |   `-- subsubdirectory
 * |   |       `-- subsubfile
 * |   `-- subdirectory2
 * |       `-- subdirectory2file
 * |-- directory2
 * |   |-- directory2file1
 * |   `-- directory2file2
 * |-- file1
 * |-- file2
 *
 * The FTP directory lists the same entries, and gxfiles://empty-dir answers with an error.
 */
import type { RemoteFilesList } from "./testingData";
import {
    directory1RecursiveResponse,
    directory1Response,
    directory2RecursiveResponse,
    pdbResponse,
    rootResponse,
    someErrorText,
    subsubdirectoryResponse,
} from "./testingData";

import FilesDialog from "./FilesDialog.vue";

function listingKey(target: string | null, recursive: string | null, writeIntent: string | null = null) {
    return `${target}?recursive=${recursive}&write_intent=${writeIntent ?? "false"}`;
}

const listings = new Map<string, RemoteFilesList>([
    [listingKey("gxfiles://pdb-gzip", "false"), pdbResponse],
    [listingKey("gxfiles://pdb-gzip/directory1", "false"), directory1Response],
    [listingKey("gxfiles://pdb-gzip/directory1", "true"), directory1RecursiveResponse],
    [listingKey("gxfiles://pdb-gzip/directory2", "true"), directory2RecursiveResponse],
    [listingKey("gxfiles://pdb-gzip/directory1/subdirectory1", "false"), subsubdirectoryResponse],
    [listingKey("gxftp://", "false"), pdbResponse],
]);

const failingListings = new Set([listingKey("gxfiles://empty-dir", "false")]);

const remoteFiles = [
    http.get("/api/remote_files/plugins", ({ response }) => response(200).json(rootResponse)),
    http.get("/api/remote_files", ({ response, query }) => {
        const key = listingKey(query.get("target"), query.get("recursive"), query.get("write_intent"));
        if (failingListings.has(key)) {
            return response("4XX").json({ err_msg: someErrorText, err_code: 400 }, { status: 400 });
        }
        const listing = listings.get(key);
        if (!listing) {
            return response("5XX").json({ err_msg: "No mocked response found", err_code: 500 }, { status: 500 });
        }
        return response(200).json(listing, { headers: { total_matches: listing.length.toString() } });
    }),
];

function fileSourceTemplates(templates: FileSourceTemplateSummary[]) {
    return http.get("/api/file_source_templates", ({ response }) => response(200).json(templates));
}

const meta = {
    title: "Files/FilesDialog",
    component: FilesDialog,
    args: { multiple: true },
    parameters: {
        msw: {
            handlers: {
                configuration: configurationHandler({ ftp_upload_site: "Test ftp upload site" }),
                remoteFiles,
                templates: fileSourceTemplates([]),
            },
        },
    },
} satisfies Meta<typeof FilesDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const MultipleFiles: Story = {};

const withTemplates = {
    msw: { handlers: { templates: fileSourceTemplates([{ id: "test_template" } as FileSourceTemplateSummary]) } },
};

export const MultipleFilesWithTemplates: Story = { parameters: withTemplates };

export const SingleFileWithTemplates: Story = { args: { multiple: false }, parameters: withTemplates };

export const Directories: Story = { args: { multiple: false, mode: "directory" } };

export const NonRecursiveFileSource: Story = {
    parameters: {
        msw: {
            handlers: {
                remoteFiles: [
                    http.get("/api/remote_files/plugins", ({ response }) =>
                        response(200).json(
                            rootResponse.map((plugin) =>
                                plugin.id === "pdb-gzip"
                                    ? { ...plugin, supports: { ...plugin.supports, recursive: false } }
                                    : plugin,
                            ),
                        ),
                    ),
                    ...remoteFiles.slice(1),
                ],
            },
        },
    },
};
