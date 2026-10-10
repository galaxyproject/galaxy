import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, fn } from "storybook/test";

import ExportForm from "./ExportForm.vue";

/** An empty form; export stays disabled until a directory and name are set. */
const meta = {
    title: "Common/ExportForm",
    component: ExportForm,
} satisfies Meta<typeof ExportForm>;

export default meta;
type Story = StoryObj<typeof meta>;
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

const NAME = "export.tar.gz";
const DIRECTORY = "gxfiles://";

/** The directory input, found by the description that asks for a repository to export `what` to. */
function directoryInput({ canvas }: PlayContext, what = "history archive") {
    return canvas.getByRole("textbox", { description: `Select a 'repository' to export ${what} to.` });
}

function nameInput({ canvas }: PlayContext) {
    return canvas.getByRole("textbox", { description: "Give the exported file a name." });
}

function exportButton({ canvas }: PlayContext) {
    return canvas.getByRole("button", { name: "Export" });
}

/** Types into the directory input without clicking it, since a click opens the file browser. */
async function enterDirectory(context: PlayContext) {
    directoryInput(context).focus();
    await context.userEvent.keyboard(DIRECTORY);
}

/** GButton marks itself disabled with `aria-disabled` only, so `toBeDisabled` can't see it. */
async function expectExportDisabled(context: PlayContext, disabled: boolean) {
    if (disabled) {
        await expect(exportButton(context)).toHaveAttribute("aria-disabled", "true");
    } else {
        await expect(exportButton(context)).not.toHaveAttribute("aria-disabled");
    }
}

/** Clicks Export and sees it export exactly once, to the directory under the name. */
async function clickExport(context: PlayContext) {
    const { args, userEvent, step } = context;
    await step("Click Export to export the file to the directory", async () => {
        await expect(args.onExport).not.toHaveBeenCalled();
        await userEvent.click(exportButton(context));
        await expect(args.onExport).toHaveBeenCalledTimes(1);
        await expect(args.onExport).toHaveBeenCalledWith(DIRECTORY, NAME);
    });
}

/** Exporting a history archive, as the history export's remote-file tab asks for it. */
export const HistoryArchive: Story = {
    args: { what: "history archive" },
    play: async (context) => {
        await context.step("See the form ask for a repository to export the history archive to", async () => {
            await expect(directoryInput(context, "history archive")).toBeVisible();
        });
    },

    // TODO a11y: label-title-only (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Exporting a history, as the archive dialog's repository tab asks for it. */
export const History: Story = {
    args: { what: "history" },
    play: async (context) => {
        await context.step("See the form ask for a repository to export the history to", async () => {
            await expect(directoryInput(context, "history")).toBeVisible();
        });
    },

    // TODO a11y: label-title-only (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Fills in one input at a time, then both, and exports. */
export const ExportsNamedFile: Story = {
    args: { ...HistoryArchive.args, onExport: fn() },
    play: async (context) => {
        const { args, userEvent, step } = context;
        await step("See export disabled while both inputs are empty, so clicking it does nothing", async () => {
            await expectExportDisabled(context, true);
            await userEvent.click(exportButton(context));
            await expect(args.onExport).not.toHaveBeenCalled();
        });
        await step("Name the file; export stays disabled without a directory", async () => {
            await userEvent.type(nameInput(context), NAME);
            await expectExportDisabled(context, true);
        });
        await step("Swap the name for a directory; export stays disabled without a name", async () => {
            await userEvent.clear(nameInput(context));
            await enterDirectory(context);
            await expectExportDisabled(context, true);
        });
        await step("Name the file again; export is enabled", async () => {
            await userEvent.type(nameInput(context), NAME);
            await expectExportDisabled(context, false);
        });
        await clickExport(context);
    },

    // TODO a11y: label-title-only (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Exports, then empties the form for the next export. */
export const ClearsAfterExport: Story = {
    args: { ...HistoryArchive.args, clearInputAfterExport: true, onExport: fn() },
    play: async (context) => {
        await context.step("Name the file and pick a directory", async () => {
            await context.userEvent.type(nameInput(context), NAME);
            await enterDirectory(context);
            await expectExportDisabled(context, false);
        });
        await clickExport(context);
        await context.step("See both inputs cleared and export disabled again", async () => {
            await expect(nameInput(context)).toHaveValue("");
            await expect(directoryInput(context)).toHaveValue("");
            await expectExportDisabled(context, true);
        });
    },

    // TODO a11y: label-title-only (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};
