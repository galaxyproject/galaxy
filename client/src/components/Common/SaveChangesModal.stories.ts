import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withToasts } from "@tests/test-data/toasts";
import { expect, waitFor, within } from "storybook/test";
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
