import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeFileSource } from "@tests/test-data/fileSources";
import { expect, fn, within } from "storybook/test";

import { http } from "@/api/client/__mocks__/http";
import type { BrowsableFilesSourcePlugin } from "@/api/remoteFiles";

import HistoryExportWizard from "./HistoryExportWizard.vue";

const posixSource = getFakeFileSource({
    id: "test-posix-source",
    type: "posix",
    label: "TestSource",
    doc: "For testing",
    writable: true,
    browsable: true,
    requires_roles: undefined,
    requires_groups: undefined,
    uri_root: "gxfiles://test-posix-source",
});

const zenodo = getFakeFileSource({
    id: "zenodo",
    type: "rdm",
    label: "Zenodo",
    doc: "For testing",
    writable: true,
    browsable: true,
    uri_root: "zenodo://",
});

const userZenodo = getFakeFileSource({
    id: "998c5bba-b18f-4223-9c93-0f36fa2fdae8",
    type: "zenodo",
    label: "My Zenodo",
    doc: "My integration with Zenodo",
    browsable: true,
    writable: true,
    requires_roles: null,
    requires_groups: null,
    url: "https://zenodo.org/",
    supports: { pagination: true, search: true, sorting: false },
    uri_root: "gxuserfiles://998c5bba-b18f-4223-9c93-0f36fa2fdae8",
});

/** The file sources the user can export to. */
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
    title: "History/Export/HistoryExportWizard",
    component: HistoryExportWizard,
    args: { historyId: "fake-history-id", historyName: "Test History", isBusy: false },
    parameters: fileSources([]),
} satisfies Meta<typeof HistoryExportWizard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const DownloadOnly: Story = {};

export const WithRemoteFileSource: Story = { parameters: fileSources([posixSource]) };

export const WithZenodo: Story = { parameters: fileSources([zenodo]) };

export const WithUserAndDefaultZenodo: Story = { parameters: fileSources([zenodo, userZenodo]) };

type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

function next({ canvas, userEvent }: PlayContext) {
    return userEvent.click(canvas.getByRole("button", { name: "Next" }));
}

export const ExportsDirectDownload: Story = {
    args: { onOnExport: fn() },
    play: async (context) => {
        const { args, canvas, userEvent, step } = context;
        await step("See the two export formats", async () => {
            const instructions = canvas.getByText(/Select the format you would like to export/);
            await expect(instructions).toBeVisible();
            // The step's content holds its instructions and body; only format cards have headings there.
            const stepContent = within(instructions.parentElement!);
            const formats = stepContent.getAllByRole("heading");
            await expect(formats.map((heading) => heading.textContent?.trim())).toEqual(["RO-Crate", "Compressed TGZ"]);
            for (const format of formats) {
                await expect(format).toBeVisible();
            }
        });
        await step("Keep the default format", () => next(context));
        await step("Choose direct download", async () => {
            const download = await canvas.findByText("Temporary Direct Download");
            await expect(download).toBeVisible();
            await userEvent.click(download);
            await next(context);
        });
        await step("Export", () => userEvent.click(canvas.getByRole("button", { name: "Generate Download Link" })));
        await expect(args.onOnExport).toHaveBeenCalledWith(
            expect.objectContaining({ destination: "download", modelStoreFormat: "rocrate.zip" }),
        );
    },

    // TODO a11y: button-name (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

export const SuggestsRemoteFileName: Story = {
    parameters: {
        ...fileSources([posixSource]),
        // TODO a11y: button-name, label-title-only (2026-10-10 audit).
        a11y: { test: "todo" },
    },
    play: async (context) => {
        const { canvas, userEvent, step } = context;
        await step("Keep the default format", () => next(context));
        await step("Choose the repository", async () => {
            const repository = await canvas.findByText("Repository");
            await expect(repository).toBeVisible();
            await userEvent.click(repository);
            await next(context);
        });
        await step("Enter a directory", async () => {
            const directory = canvas.getByRole("textbox", {
                description: "Select a 'repository' to export history to.",
            });
            await expect(directory).toBeVisible();
            await expect(canvas.getByRole("button", { name: "Next" })).toBeDisabled();
            // Typing without clicking: a click opens the file browser.
            directory.focus();
            await userEvent.keyboard("gxfiles://test-posix-source/test-directory");
            await expect(canvas.getByRole("button", { name: "Next" })).toBeEnabled();
            await next(context);
        });
        await step("See the history name suggested as the file name", async () => {
            await expect(canvas.getByPlaceholderText(/Test History/)).toBeVisible();
        });
    },
};

export const SetsUpZenodoDraftRecord: Story = {
    parameters: {
        ...fileSources([zenodo]),
        // TODO a11y: button-name (2026-10-10 audit).
        a11y: { test: "todo" },
    },
    play: async (context) => {
        const { canvas, userEvent, step } = context;
        await step("Keep the default format", () => next(context));
        await step("Choose Zenodo", async () => {
            const zenodoLogo = await canvas.findByRole("img", { name: "Zenodo Logo" });
            await expect(zenodoLogo).toBeVisible();
            await userEvent.click(zenodoLogo);
            await next(context);
        });
        await step("See the draft record setup", async () => {
            await expect(await canvas.findByText("Select or create a draft record to export to")).toBeVisible();
            await expect(canvas.getByRole("radio", { name: "Export to new record" })).toBeChecked();
        });
    },
};

export const PrefersUserZenodo: Story = {
    parameters: {
        ...fileSources([zenodo, userZenodo]),
        // TODO a11y: button-name, link-in-text-block (2026-10-10 audit).
        a11y: { test: "todo" },
    },
    play: async (context) => {
        await context.step("Keep the default format", () => next(context));
        await expect(await context.canvas.findByText("My Zenodo")).toBeVisible();
    },
};
