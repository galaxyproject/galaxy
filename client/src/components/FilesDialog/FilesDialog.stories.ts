import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, waitFor, within } from "storybook/test";

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

type PlayContext = Parameters<NonNullable<Story["play"]>>[0];
type Canvas = PlayContext["canvas"];

/** The file sources at the root, user-defined ones first. */
const SOURCES = ["My own FTP", "FTP Directory", "PDB", "Empty Directory"];
/** The entries of the PDB source, as the API lists them. */
const PDB_ENTRIES = ["file2", "file1", "directory2", "directory1"];
const DIRECTORY1_ENTRIES = ["directory1file2", "subdirectory1", "subdirectory2", "directory1file1", "directory1file3"];

/** The table's body rows. */
function rows(canvas: Canvas) {
    return canvas.getAllByRole("row").filter((row) => within(row).queryAllByRole("cell").length > 0);
}

/** A row's name: the text of its first cell that isn't a selection checkbox. */
function nameOf(row: HTMLElement) {
    const label = within(row)
        .getAllByRole("cell")
        .find((cell) => !within(cell).queryByRole("checkbox"));
    return label?.textContent?.trim();
}

function rowNamed(canvas: Canvas, name: string) {
    const row = rows(canvas).find((candidate) => nameOf(candidate) === name);
    if (!row) {
        throw new Error(`no row named "${name}"`);
    }
    return row;
}

/** Every row shares the checkbox label, so find it within the row. */
function checkboxOf(canvas: Canvas, name: string) {
    return within(rowNamed(canvas, name)).getByRole("checkbox", { name: "Select for bulk actions" });
}

/** Waits for the listing to read `names`, in order. */
async function seeRows(canvas: Canvas, names: string[], options?: { timeout: number }) {
    await waitFor(() => expect(rows(canvas).map(nameOf)).toEqual(names), options);
}

async function seeChecked(canvas: Canvas, checked: string[], unchecked: string[] = []) {
    await waitFor(async () => {
        for (const name of checked) {
            await expect(checkboxOf(canvas, name)).toBeChecked();
        }
    });
    for (const name of unchecked) {
        await expect(checkboxOf(canvas, name)).not.toBeChecked();
        await expect(checkboxOf(canvas, name)).not.toBePartiallyChecked();
    }
}

/** Opens a source or directory by clicking its name, and waits for its listing. */
async function openNamed({ canvas, step, userEvent }: PlayContext, name: string, entries: string[]) {
    await step(`Open ${name}; see ${entries.join(", ")}`, async () => {
        await userEvent.click(canvas.getByRole("button", { name }));
        await seeRows(canvas, entries);
    });
}

async function goBack({ canvas, step, userEvent }: PlayContext, entries: string[]) {
    await step(`Go back; see ${entries.join(", ")}`, async () => {
        await userEvent.click(canvas.getByRole("button", { name: "Back" }));
        await seeRows(canvas, entries);
    });
}

async function toggle({ canvas, userEvent }: PlayContext, name: string) {
    await userEvent.click(checkboxOf(canvas, name));
}

async function seeSelectButton(canvas: Canvas, name: string, enabled: boolean) {
    const button = canvas.getByRole("button", { name });
    if (enabled) {
        await waitFor(() => expect(button).not.toHaveAttribute("aria-disabled"));
    } else {
        await expect(button).toHaveAttribute("aria-disabled", "true");
    }
}

/** Waits for the sources at the root, with no button to create one. */
async function seeSources({ canvas, step }: PlayContext, { canCreate }: { canCreate: boolean }) {
    await step(`See the sources, user-defined first${canCreate ? ", and a button to create one" : ""}`, async () => {
        await seeRows(canvas, SOURCES, { timeout: 5000 });
        // the button waits on the templates request, which answers apart from the sources
        if (canCreate) {
            await expect(await canvas.findByRole("button", { name: /^Create new/ })).toBeVisible();
        } else {
            await expect(canvas.queryByRole("button", { name: /^Create new/ })).not.toBeInTheDocument();
        }
    });
}

/** Opens the failing source, sees its error, and goes back to the sources. */
async function recoverFromSourceError(context: PlayContext) {
    const { canvas, step, userEvent } = context;
    await seeSources(context, { canCreate: false });
    await step("See no error yet", async () => {
        await expect(canvas.queryByRole("alert")).not.toBeInTheDocument();
    });
    await step("Open Empty Directory; see the error instead of a listing", async () => {
        await userEvent.click(canvas.getByRole("button", { name: "Empty Directory" }));
        await expect(await canvas.findByRole("alert")).toHaveTextContent(/^some error text$/);
        await expect(canvas.queryAllByRole("row")).toHaveLength(0);
    });
    await goBack(context, SOURCES);
    await step("See the error gone", async () => {
        await expect(canvas.queryByRole("alert")).not.toBeInTheDocument();
    });
}

export const MultipleFiles: Story = {
    play: async (context) => {
        await seeSources(context, { canCreate: false });
    },

    // TODO a11y: button-name, nested-interactive, target-size (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Ticking files selects them; with none ticked there's nothing to select. */
export const SelectsFiles: Story = {
    play: async (context) => {
        const { canvas, step } = context;
        await seeSources(context, { canCreate: false });
        await openNamed(context, "PDB", PDB_ENTRIES);
        await step("See nothing selected and Select unavailable", async () => {
            await seeChecked(canvas, [], PDB_ENTRIES);
            await seeSelectButton(canvas, "Select", false);
        });
        // The browser ticks a clicked box itself, so the select-all box shows what the dialog made of it.
        const selectAll = canvas.getByRole("checkbox", { name: "Select all for bulk actions" });
        await step("Tick both files; only they are selected and Select is available", async () => {
            await toggle(context, "file2");
            await toggle(context, "file1");
            await waitFor(() => expect(selectAll).toBePartiallyChecked());
            await seeChecked(canvas, ["file2", "file1"], ["directory2", "directory1"]);
            await seeSelectButton(canvas, "Select", true);
        });
        await step("Untick both; Select is unavailable again", async () => {
            await toggle(context, "file2");
            await toggle(context, "file1");
            await waitFor(() => expect(selectAll).not.toBePartiallyChecked());
            await expect(selectAll).not.toBeChecked();
            await seeChecked(canvas, [], PDB_ENTRIES);
            await seeSelectButton(canvas, "Select", false);
        });
    },

    // TODO a11y: button-name, nested-interactive, target-size (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Ticking a directory selects everything in it; unticking one file leaves the directory partly selected. */
export const SelectsDirectoryContents: Story = {
    play: async (context) => {
        const { canvas, step } = context;
        await seeSources(context, { canCreate: false });
        await openNamed(context, "PDB", PDB_ENTRIES);
        await step("Tick directory1", async () => {
            await toggle(context, "directory1");
            await seeChecked(canvas, ["directory1"]);
        });
        await openNamed(context, "directory1", DIRECTORY1_ENTRIES);
        await step("See everything in it selected", async () => {
            await seeChecked(canvas, DIRECTORY1_ENTRIES);
            const selectAll = canvas.getByRole("checkbox", { name: "Select all for bulk actions" });
            await expect(selectAll).toBeChecked();
            await expect(selectAll).not.toBePartiallyChecked();
        });
        await step("Untick directory1file2", async () => {
            await toggle(context, "directory1file2");
            await seeChecked(canvas, [], ["directory1file2"]);
        });
        await goBack(context, PDB_ENTRIES);
        await step("See directory1 partly selected", async () => {
            await expect(checkboxOf(canvas, "directory1")).toBePartiallyChecked();
        });
    },

    // TODO a11y: button-name, nested-interactive, target-size (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Unticking a subdirectory of a ticked directory keeps the rest selected. */
export const UnselectsSubdirectory: Story = {
    play: async (context) => {
        const { canvas, step } = context;
        await seeSources(context, { canCreate: false });
        await openNamed(context, "PDB", PDB_ENTRIES);
        await step("Tick directory1", async () => {
            await toggle(context, "directory1");
            await seeChecked(canvas, ["directory1"]);
        });
        await openNamed(context, "directory1", DIRECTORY1_ENTRIES);
        await openNamed(context, "subdirectory1", ["subsubdirectory"]);
        await step("Untick subsubdirectory; nothing here is selected", async () => {
            await seeChecked(canvas, ["subsubdirectory"]);
            await toggle(context, "subsubdirectory");
            await seeChecked(canvas, [], ["subsubdirectory"]);
            const selectAll = canvas.getByRole("checkbox", { name: "Select all for bulk actions" });
            await expect(selectAll).not.toBeChecked();
            await expect(selectAll).not.toBePartiallyChecked();
        });
        await goBack(context, DIRECTORY1_ENTRIES);
        await goBack(context, PDB_ENTRIES);
        await step("See directory1 partly selected", async () => {
            await expect(checkboxOf(canvas, "directory1")).toBePartiallyChecked();
        });
    },

    // TODO a11y: button-name, nested-interactive, target-size (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Select all in a source selects everything below it too. */
export const SelectsAll: Story = {
    play: async (context) => {
        const { canvas, step, userEvent } = context;
        await seeSources(context, { canCreate: false });
        await openNamed(context, "PDB", PDB_ENTRIES);
        await step("Select all", async () => {
            await userEvent.click(canvas.getByRole("checkbox", { name: "Select all for bulk actions" }));
            await seeChecked(canvas, PDB_ENTRIES);
        });
        await openNamed(context, "directory1", DIRECTORY1_ENTRIES);
        await step("See everything in directory1 selected", () => seeChecked(canvas, DIRECTORY1_ENTRIES));
        await goBack(context, PDB_ENTRIES);
        await step("See everything still selected", () => seeChecked(canvas, PDB_ENTRIES));
    },

    // TODO a11y: button-name, nested-interactive, target-size (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** The FTP directory explains how to upload to it; other sources don't. */
export const ShowsFtpHelp: Story = {
    play: async (context) => {
        const { canvas, step } = context;
        await seeSources(context, { canCreate: false });
        // FTP first: the help also waits for the config, which the PDB check then can't race.
        await openNamed(context, "FTP Directory", PDB_ENTRIES);
        await step("See how to upload via FTP", async () => {
            const help = canvas.getByRole("status");
            await expect(help).toHaveTextContent(
                /^This Galaxy server allows you to upload files via FTP\. To upload some files, log in to the FTP server at Test ftp upload site using your Galaxy credentials\. For help visit the tutorial\.$/,
            );
            await expect(within(help).getByRole("strong")).toHaveTextContent(/^Test ftp upload site$/);
            await expect(within(help).getByRole("link", { name: "tutorial" })).toHaveAttribute(
                "href",
                "https://galaxyproject.org/ftp-upload/",
            );
        });
        await goBack(context, SOURCES);
        await openNamed(context, "PDB", PDB_ENTRIES);
        await step("See no FTP help in another source", async () => {
            await expect(canvas.queryByText(/upload files via FTP/)).not.toBeInTheDocument();
        });
    },

    // TODO a11y: button-name, nested-interactive, target-size (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** A source that fails to list shows its error, and Back returns to the sources. */
export const RecoversFromSourceError: Story = {
    play: recoverFromSourceError,

    // TODO a11y: button-name, nested-interactive, target-size (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

const withTemplates = {
    msw: { handlers: { templates: fileSourceTemplates([{ id: "test_template" } as FileSourceTemplateSummary]) } },
};

export const MultipleFilesWithTemplates: Story = {
    parameters: {
        ...withTemplates,
        // TODO a11y: button-name, nested-interactive, target-size (2026-10-10 audit).
        a11y: { test: "todo" },
    },
    play: async (context) => {
        await seeSources(context, { canCreate: true });
    },
};

export const SingleFileWithTemplates: Story = {
    args: { multiple: false },
    parameters: {
        ...withTemplates,
        // TODO a11y: button-name, nested-interactive, target-size (2026-10-10 audit).
        a11y: { test: "todo" },
    },
    play: async (context) => {
        await seeSources(context, { canCreate: true });
    },
};

/** New sources are created from the root only, not from inside one. */
export const CreatesSourcesFromRootOnly: Story = {
    ...SingleFileWithTemplates,
    play: async (context) => {
        await seeSources(context, { canCreate: true });
        await openNamed(context, "PDB", PDB_ENTRIES);
        await context.step("See no button to create a source", async () => {
            await expect(context.canvas.queryByRole("button", { name: /^Create new/ })).not.toBeInTheDocument();
        });
    },

    // TODO a11y: button-name, nested-interactive, target-size (2026-10-10 audit).
    parameters: { ...SingleFileWithTemplates.parameters, a11y: { test: "todo" } },
};

export const Directories: Story = {
    args: { multiple: false, mode: "directory" },
    // TODO a11y: button-name, nested-interactive, target-size (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

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
/** Choosing a folder lists only directories, at every level. */
export const ListsDirectoriesOnly: Story = {
    ...Directories,
    play: async (context) => {
        await seeSources(context, { canCreate: false });
        await openNamed(context, "PDB", ["directory2", "directory1"]);
        await openNamed(context, "directory1", ["subdirectory1", "subdirectory2"]);
    },

    // TODO a11y: button-name, nested-interactive, target-size (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** A folder is chosen by opening it: the root itself can't be chosen. */
export const SelectsFolderByOpening: Story = {
    ...Directories,
    play: async (context) => {
        await seeSources(context, { canCreate: false });
        // SelectionDialog's "Select" default hides its "Select this folder" label (BUGS_FOUND).
        await context.step("See Select unavailable at the root", () =>
            seeSelectButton(context.canvas, "Select", false),
        );
        await openNamed(context, "PDB", ["directory2", "directory1"]);
        await context.step("See Select available", () => seeSelectButton(context.canvas, "Select", true));
    },

    // TODO a11y: button-name, nested-interactive, target-size (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

export const DirectoriesRecoverFromSourceError: Story = {
    ...Directories,
    play: recoverFromSourceError,

    // TODO a11y: button-name, nested-interactive, target-size (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};
