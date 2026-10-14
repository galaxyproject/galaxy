import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeAnonymousUser, getFakeHistorySummaryExtended } from "@tests/test-data";
import { viewedBy, withCurrentUser } from "@tests/test-data/currentUser";
import { withToasts } from "@tests/test-data/toasts";
import { expect, waitFor, within } from "storybook/test";

import { ANALYSIS_HISTORY, HISTORY_VIEWER, historyOperationsStory } from "./test_fixtures";

import HistoryOptions from "./HistoryOptions.vue";

const deletedHistory = getFakeHistorySummaryExtended({ ...ANALYSIS_HISTORY, deleted: true });
const anonymousHistory = getFakeHistorySummaryExtended({ ...ANALYSIS_HISTORY, user_id: null });
const anonymousOperations = historyOperationsStory(anonymousHistory);
const sharedHistory = getFakeHistorySummaryExtended({ ...ANALYSIS_HISTORY, user_id: "d0ae172bc345689f" });

const meta = {
    title: "History/HistoryOptions",
    component: HistoryOptions,
    decorators: [withCurrentUser(() => HISTORY_VIEWER), withToasts],
    args: { history: ANALYSIS_HISTORY },
} satisfies Meta<typeof HistoryOptions>;

export default meta;
type Story = StoryObj<typeof meta>;

/** An owned history offers copy, delete, export and sharing operations. */
export const OwnedHistory: Story = { ...historyOperationsStory() };

/** A deleted history can be permanently removed; its purge option is already selected. */
export const DeletedHistory: Story = {
    args: { history: deletedHistory },
    ...historyOperationsStory(deletedHistory),
};

/** A session history keeps basic operations available and explains account-only options. */
export const AnonymousHistory: Story = {
    args: { history: anonymousHistory },
    ...anonymousOperations,
    parameters: {
        ...anonymousOperations.parameters,
        ...viewedBy(getFakeAnonymousUser()),
    },
};

/** Another user's accessible history offers copy and read-only views rather than owner actions. */
export const UnownedHistory: Story = {
    args: { history: sharedHistory },
    ...historyOperationsStory(sharedHistory),
};

/** Open the active history's deletion confirmation without submitting it. */
export const OpensDeleteConfirmation: Story = {
    ...historyOperationsStory(),
    play: async ({ canvas, userEvent, step }) => {
        await step("Open the active history menu with no deletion dialog", async () => {
            const options = canvas.getByRole("button", { name: "History Options" });
            await expect(options).toBeVisible();
            await expect(canvas.queryByRole("dialog")).not.toBeInTheDocument();
            await userEvent.click(options);
            await expect(await canvas.findByRole("menuitem", { name: "Delete History" })).toBeVisible();
            await expect(
                canvas.queryByRole("menuitem", { name: "Permanently Delete History" }),
            ).not.toBeInTheDocument();
        });
        await step("Read the confirmation and optional permanent deletion choice", async () => {
            await userEvent.click(canvas.getByRole("menuitem", { name: "Delete History" }));
            const dialog = within(await canvas.findByRole("dialog"));
            await expect(dialog.getByRole("heading", { name: "Delete History?" })).toBeVisible();
            await expect(dialog.getByRole("button", { name: "Delete" })).toBeVisible();
            await expect(dialog.getByText(ANALYSIS_HISTORY.name, { exact: true })).toBeVisible();
            const purge = dialog.getByRole("checkbox", { name: "Yes, permanently delete this history." });
            await expect(purge).toBeEnabled();
            await expect(purge).not.toBeChecked();
            await userEvent.click(purge);
            await expect(purge).toBeChecked();
        });
        await step("Cancel and return to the history menu", async () => {
            await userEvent.click(within(canvas.getByRole("dialog")).getByRole("button", { name: "Cancel" }));
            await waitFor(() => expect(canvas.queryByRole("dialog")).not.toBeInTheDocument());
            await expect(canvas.getByRole("button", { name: "History Options" })).toBeVisible();
            await userEvent.click(canvas.getByRole("button", { name: "History Options" }));
            await userEvent.click(canvas.getByRole("menuitem", { name: "Delete History" }));
            await expect(
                within(await canvas.findByRole("dialog")).getByRole("heading", {
                    name: "Delete History?",
                }),
            ).toBeVisible();
            await expect(
                within(canvas.getByRole("dialog")).getByRole("checkbox", {
                    name: "Yes, permanently delete this history.",
                }),
            ).not.toBeChecked();
        });
    },
};

/** Deleted history confirmation requires permanent deletion. */
export const OpensPermanentDeleteConfirmation: Story = {
    args: { history: deletedHistory },
    ...historyOperationsStory(deletedHistory),
    play: async ({ canvas, userEvent, step }) => {
        await step("Open the deleted history menu with no deletion dialog", async () => {
            const options = canvas.getByRole("button", { name: "History Options" });
            await expect(options).toBeVisible();
            await expect(canvas.queryByRole("dialog")).not.toBeInTheDocument();
            await userEvent.click(options);
            await expect(await canvas.findByRole("menuitem", { name: "Permanently Delete History" })).toBeVisible();
        });
        await step("Read the permanent deletion confirmation and fixed purge choice", async () => {
            await userEvent.click(canvas.getByRole("menuitem", { name: "Permanently Delete History" }));
            const dialog = within(await canvas.findByRole("dialog"));
            await expect(dialog.getByRole("heading", { name: "Permanently Delete History?" })).toBeVisible();
            await expect(dialog.getByRole("button", { name: "Delete Permanently" })).toBeVisible();
            await expect(dialog.getByText(deletedHistory.name, { exact: true })).toBeVisible();
            const purge = dialog.getByRole("checkbox", { name: "Yes, permanently delete this history." });
            await expect(purge).toBeDisabled();
            await expect(purge).toBeChecked();
        });
        await step("Cancel permanent deletion", async () => {
            await userEvent.click(within(canvas.getByRole("dialog")).getByRole("button", { name: "Cancel" }));
            await waitFor(() => expect(canvas.queryByRole("dialog")).not.toBeInTheDocument());
            await expect(canvas.getByRole("button", { name: "History Options" })).toBeVisible();
            await userEvent.click(canvas.getByRole("button", { name: "History Options" }));
            await userEvent.click(canvas.getByRole("menuitem", { name: "Permanently Delete History" }));
            await expect(
                within(await canvas.findByRole("dialog")).getByRole("heading", {
                    name: "Permanently Delete History?",
                }),
            ).toBeVisible();
        });
    },
};
