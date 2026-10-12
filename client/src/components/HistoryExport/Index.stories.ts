import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { getFakeFileSource } from "@tests/test-data/fileSources";
import { HttpResponse } from "msw";
import { expect, waitFor, within } from "storybook/test";

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
    play: async ({ canvas, step }) => {
        await step("Read the download-link view when repositories are read-only", async () => {
            await expect(
                await canvas.findByText(/No link for history export ready/, {}, { timeout: 5000 }),
            ).toBeVisible();
            await expect(
                canvas.getByRole("link", { name: "Click here to generate a new archive for this history." }),
            ).toBeVisible();
            await expect(canvas.queryByRole("tablist")).not.toBeInTheDocument();
            await expect(
                canvas.queryByRole("textbox", { description: "Select a 'repository' to export history archive to." }),
            ).not.toBeInTheDocument();
        });
    },
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

/** Choose an existing repository root, then return to the download-link view without exporting. */
export const ChoosesRepositoryDestination: Story = {
    play: async ({ canvas, canvasElement, userEvent, step }) => {
        const page = within(canvasElement.ownerDocument.body);
        await step("Read the initial download-link view", async () => {
            const linkTab = await canvas.findByRole("tab", { name: "to a link" }, { timeout: 5000 });
            await expect(linkTab).toHaveAttribute("aria-selected", "true");
            await expect(
                await canvas.findByText(/No link for history export ready/, {}, { timeout: 5000 }),
            ).toBeVisible();
            await expect(
                canvas.queryByRole("textbox", { description: "Select a 'repository' to export history archive to." }),
            ).not.toBeInTheDocument();
        });
        await step("Switch to repository export", async () => {
            await userEvent.click(canvas.getByRole("tab", { name: "to a repository" }));
            await expect(canvas.getByRole("tab", { name: "to a repository" })).toHaveAttribute("aria-selected", "true");
            await expect(canvas.getByText(/No link for history export ready/)).not.toBeVisible();
            await expect(canvas.getByRole("button", { name: "Export" })).toHaveAttribute("aria-disabled", "true");
        });
        await step("Choose the writable repository root as a destination", async () => {
            const directory = canvas.getByRole("textbox", {
                description: "Select a 'repository' to export history archive to.",
            });
            await expect(directory).toHaveValue("");
            await expect(page.queryByRole("dialog")).not.toBeInTheDocument();
            await userEvent.click(directory);
            const dialog = await page.findByRole("dialog", {}, { timeout: 5000 });
            await userEvent.click(
                await within(dialog).findByText(REPOSITORY.label, { exact: true }, { timeout: 5000 }),
            );
            const select = within(dialog).getByRole("button", { name: "Select" });
            await waitFor(() => expect(select).not.toHaveAttribute("aria-disabled", "true"));
            await userEvent.click(select);
            await waitFor(() => expect(page.queryByRole("dialog")).not.toBeInTheDocument());
            await expect(directory).toHaveValue(REPOSITORY.uri_root);
        });
        await step("Return to the download-link view", async () => {
            await userEvent.click(canvas.getByRole("tab", { name: "to a link" }));
            await expect(canvas.getByRole("tab", { name: "to a link" })).toHaveAttribute("aria-selected", "true");
            await expect(
                await canvas.findByText(/No link for history export ready/, {}, { timeout: 5000 }),
            ).toBeVisible();
            await expect(
                canvas.queryByRole("textbox", { description: "Select a 'repository' to export history archive to." }),
            ).not.toBeInTheDocument();
        });
    },
};
