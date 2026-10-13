import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { seeToasts, withToasts } from "@tests/test-data/toasts";
import { expect, userEvent, waitFor, within } from "storybook/test";
import { computed, h, ref } from "vue";

import SaveChangesModal from "./SaveChangesModal.vue";

interface Args {
    savedText: string;
    text: string;
    saveFails: boolean;
}

const savedText = "# RNA-seq notes\n\nCounts are ready to review.";
const unsavedText = `${savedText}\n\nCompare the treatment groups next.`;

const meta = {
    title: "Common/SaveChangesModal",
    decorators: [withToasts],
    args: { savedText, text: savedText, saveFails: false },
    render: (args) => ({
        setup() {
            const saved = ref(args.savedText);
            const content = ref(args.text);
            const preview = ref<string | null>(null);
            const modal = ref<InstanceType<typeof SaveChangesModal> | null>(null);
            const hasChanges = computed(() => content.value !== saved.value);

            async function save() {
                if (args.saveFails) {
                    throw new Error("The page could not be saved.");
                }
                saved.value = content.value;
            }

            function discard() {
                content.value = saved.value;
            }

            function openPreview() {
                modal.value?.guardNavigation(() => {
                    preview.value = content.value;
                });
            }

            return () =>
                h("div", { class: "d-flex flex-column", style: "gap: 1rem" }, [
                    h("h1", "RNA-seq page editor"),
                    h("label", { for: "save-changes-page-content" }, "Page content"),
                    h("textarea", {
                        id: "save-changes-page-content",
                        rows: 6,
                        value: content.value,
                        onInput: (event: Event) => {
                            content.value = (event.target as HTMLTextAreaElement).value;
                        },
                    }),
                    h("p", { role: "status" }, hasChanges.value ? "Unsaved changes" : "All changes saved"),
                    h("button", { type: "button", onClick: openPreview }, "Open preview"),
                    preview.value === null
                        ? null
                        : h("section", { "aria-label": "Page preview" }, [
                              h("h2", "Page preview"),
                              h("pre", preview.value),
                          ]),
                    h(SaveChangesModal, {
                        ref: modal,
                        hasChanges: hasChanges.value,
                        onSave: save,
                        onDiscard: discard,
                    }),
                ]);
        },
    }),
    afterEach: async ({ canvasElement }) => {
        await waitFor(
            () => expect(within(canvasElement).getByRole("textbox", { name: "Page content" })).toBeVisible(),
            { timeout: 5000 },
        );
    },
} satisfies Meta<Args>;
export default meta;
type Story = StoryObj<typeof meta>;

/** Opening a floating preview needs no confirmation when the page has no changes. */
export const SavedPage: Story = {};

/** Previewing pending edits offers saving, discarding, or returning to the editor. */
export const UnsavedPage: Story = { args: { text: unsavedText } };

/** A failed save leaves the changes in the editor and reports the error as a toast. */
export const SaveFailure: Story = { args: { text: unsavedText, saveFails: true } };

async function closeWith(dialog: HTMLElement, button: HTMLElement) {
    const closed = new Promise<void>((resolve) => {
        dialog.addEventListener("close", () => resolve(), { once: true });
    });
    await userEvent.click(button);
    await closed;
}

function expectPreview(canvas: ReturnType<typeof within>, text: string) {
    const preview = within(canvas.getByRole("region", { name: "Page preview" }));
    const content = preview.getByText(/Counts are ready to review\./);
    expect(content).toBeVisible();
    expect(content.textContent).toBe(text);
}

export const PreviewsSavedPage: Story = {
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        await canvas.findByRole("textbox", { name: "Page content" }, { timeout: 5000 });
        await step("Preview a saved page without a confirmation", async () => {
            expect(canvas.getByRole("status").textContent).toBe("All changes saved");
            await userEvent.click(canvas.getByRole("button", { name: "Open preview" }));
            await canvas.findByRole("region", { name: "Page preview" });
            expectPreview(canvas, savedText);
            expect(canvas.queryByRole("dialog")).not.toBeInTheDocument();
        });
    },
};

export const SavesThenPreviews: Story = {
    ...UnsavedPage,
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        const editor = await canvas.findByRole("textbox", { name: "Page content" }, { timeout: 5000 });
        await step("Save the pending edits before opening the preview", async () => {
            expect(editor).toHaveValue(unsavedText);
            expect(canvas.getByRole("status").textContent).toBe("Unsaved changes");
            expect(canvas.queryByRole("dialog")).not.toBeInTheDocument();
            await userEvent.click(canvas.getByRole("button", { name: "Open preview" }));
            const dialog = await canvas.findByRole("dialog");
            expect(canvas.queryByRole("region", { name: "Page preview" })).not.toBeInTheDocument();
            await closeWith(dialog, within(dialog).getByRole("button", { description: "Save changes and proceed" }));
            await canvas.findByRole("region", { name: "Page preview" });
            expectPreview(canvas, unsavedText);
            expect(editor).toHaveValue(unsavedText);
            expect(canvas.getByRole("status").textContent).toBe("All changes saved");
            expect(canvas.queryByRole("dialog")).not.toBeInTheDocument();
        });
    },
};

export const DiscardsThenPreviews: Story = {
    ...UnsavedPage,
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        const editor = await canvas.findByRole("textbox", { name: "Page content" }, { timeout: 5000 });
        await step("Discard the edits and preview the last saved version", async () => {
            expect(editor).toHaveValue(unsavedText);
            expect(canvas.queryByRole("dialog")).not.toBeInTheDocument();
            await userEvent.click(canvas.getByRole("button", { name: "Open preview" }));
            const dialog = await canvas.findByRole("dialog");
            expect(canvas.queryByRole("region", { name: "Page preview" })).not.toBeInTheDocument();
            await closeWith(dialog, within(dialog).getByRole("button", { description: "Discard changes and proceed" }));
            await canvas.findByRole("region", { name: "Page preview" });
            expectPreview(canvas, savedText);
            expect(editor).toHaveValue(savedText);
            expect(canvas.getByRole("status").textContent).toBe("All changes saved");
            expect(canvas.queryByRole("dialog")).not.toBeInTheDocument();
        });
    },
};

export const CancelsThenReopens: Story = {
    ...UnsavedPage,
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        const editor = await canvas.findByRole("textbox", { name: "Page content" }, { timeout: 5000 });
        await step("Cancel the preview and keep editing the unsaved page", async () => {
            expect(canvas.queryByRole("dialog")).not.toBeInTheDocument();
            await userEvent.click(canvas.getByRole("button", { name: "Open preview" }));
            const dialog = await canvas.findByRole("dialog");
            await closeWith(
                dialog,
                within(dialog).getByRole("button", { description: "Do not run proceed and return to editor" }),
            );
            expect(editor).toHaveValue(unsavedText);
            expect(canvas.getByRole("status").textContent).toBe("Unsaved changes");
            expect(canvas.queryByRole("dialog")).not.toBeInTheDocument();
            expect(canvas.queryByRole("region", { name: "Page preview" })).not.toBeInTheDocument();
        });
        await step("Ask again on the next preview attempt", async () => {
            await userEvent.click(canvas.getByRole("button", { name: "Open preview" }));
            const dialog = await canvas.findByRole("dialog");
            expect(within(dialog).getByRole("button", { description: "Save changes and proceed" })).not.toHaveAttribute(
                "aria-disabled",
            );
            await closeWith(
                dialog,
                within(dialog).getByRole("button", { description: "Do not run proceed and return to editor" }),
            );
            expect(editor).toHaveValue(unsavedText);
            expect(canvas.queryByRole("region", { name: "Page preview" })).not.toBeInTheDocument();
        });
    },
};

export const FailedSaveThenDiscard: Story = {
    ...SaveFailure,
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        const editor = await canvas.findByRole("textbox", { name: "Page content" }, { timeout: 5000 });
        await step("Report the failed save without losing the edits or opening the preview", async () => {
            expect(canvas.queryByRole("dialog")).not.toBeInTheDocument();
            await userEvent.click(canvas.getByRole("button", { name: "Open preview" }));
            const dialog = await canvas.findByRole("dialog");
            const closed = new Promise<void>((resolve) =>
                dialog.addEventListener("close", () => resolve(), { once: true }),
            );
            await userEvent.click(within(dialog).getByRole("button", { description: "Save changes and proceed" }));
            await seeToasts(canvas, [["Error", "The page could not be saved."]]);
            await closed;
            expect(editor).toHaveValue(unsavedText);
            expect(canvas.getByRole("status").textContent).toBe("Unsaved changes");
            expect(canvas.queryByRole("dialog")).not.toBeInTheDocument();
            expect(canvas.queryByRole("region", { name: "Page preview" })).not.toBeInTheDocument();
        });
        await step("Offer enabled choices again and discard to open the saved preview", async () => {
            await userEvent.click(canvas.getByRole("button", { name: "Open preview" }));
            const dialog = await canvas.findByRole("dialog");
            const choices = within(dialog);
            for (const description of [
                "Do not run proceed and return to editor",
                "Discard changes and proceed",
                "Save changes and proceed",
            ]) {
                expect(choices.getByRole("button", { description })).not.toHaveAttribute("aria-disabled");
            }
            await closeWith(dialog, choices.getByRole("button", { description: "Discard changes and proceed" }));
            await canvas.findByRole("region", { name: "Page preview" });
            expectPreview(canvas, savedText);
            expect(editor).toHaveValue(savedText);
            expect(canvas.getByRole("status").textContent).toBe("All changes saved");
            expect(canvas.queryByRole("dialog")).not.toBeInTheDocument();
        });
    },
};
