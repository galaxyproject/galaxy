import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentHistory } from "@tests/test-data/currentHistory";
import { exactly } from "@tests/test-data/text";
import { expect, waitFor, within } from "storybook/test";
import { h, ref } from "vue";

import { toolBoxState, withToolBoxState } from "@/components/Panels/test_fixtures";
import { CURRENT_HISTORY } from "@/components/SelectionField/test_fixtures";
import reportSteps from "@/components/Workflow/Editor/test-data/simple_steps.json";
import { clearDrag, setDrag } from "@/utils/setDrag";

import {
    MARKDOWN_COLLECTION,
    MARKDOWN_DATASET,
    MARKDOWN_WORKFLOW,
    markdownToolboxHandlers,
    withMarkdownDrag,
} from "../test_fixtures";

import TextEditor from "./TextEditor.vue";

const meta = {
    title: "Markdown/Editor/TextEditor",
    component: TextEditor,
    decorators: [withCurrentHistory(CURRENT_HISTORY), withToolBoxState, withMarkdownDrag],
    args: { markdownText: "", mode: "page", title: "RNA-seq analysis notes" },
    render: (args) => ({
        setup() {
            const content = ref(args.markdownText);
            return () =>
                h("div", { class: "d-flex flex-column", style: "height: 480px" }, [
                    h("div", { class: "d-flex flex-wrap p-2", style: "gap: 1rem" }, [
                        ...[MARKDOWN_DATASET, MARKDOWN_COLLECTION, MARKDOWN_WORKFLOW].map((item) =>
                            h(
                                "div",
                                {
                                    draggable: true,
                                    class: "border rounded p-2",
                                    onDragstart: (event: DragEvent) => setDrag(event, item),
                                    onDragend: clearDrag,
                                },
                                item.name ?? "",
                            ),
                        ),
                    ]),
                    h("div", { class: "d-flex flex-grow-1", style: "min-height: 0" }, [
                        h(TextEditor, {
                            ...args,
                            markdownText: content.value,
                            onUpdate: (value: string) => {
                                content.value = value;
                            },
                        }),
                    ]),
                ]);
        },
    }),
    afterEach: async ({ canvasElement }) => {
        await waitFor(
            () => expect(within(canvasElement).getByRole("textbox", { name: "markdown text editor" })).toBeVisible(),
            { timeout: 5000 },
        );
    },
    parameters: {
        ...toolBoxState({ tools: [], toolSections: { default: {} } }),
        msw: { handlers: markdownToolboxHandlers },
    },
} satisfies Meta<typeof TextEditor>;
export default meta;
type Story = StoryObj<typeof meta>;

/** Write a page and insert objects from its toolbox or by dragging history items above. */
export const PageWithToolbox: Story = {};

/** Continue a page that already has analysis notes, keeping the cursor's insertion point. */
export const PageWithExistingContent: Story = {
    args: { markdownText: "# RNA-seq analysis\n\nCounts are ready to review.\n" },
};

/** The surrounding page editor can hide its toolbox to make more space for the text. */
export const CompactPage: Story = {
    args: { hideToolbox: true },
};

/** Report templates insert workflow labels; history drag payloads are ignored in this mode. */
export const WorkflowReportTemplate: Story = {
    args: { mode: "report", steps: reportSteps, title: "RNA-seq workflow report" },
};

/** Native history drags insert both object types without discarding existing page notes. */
export const InsertsDraggedHistoryItems: Story = {
    args: PageWithExistingContent.args,
    play: async ({ canvasElement, userEvent, step }) => {
        await step("Insert a dataset and collection without losing existing notes", async () => {
            const canvas = within(canvasElement);
            const editor = canvas.getByRole("textbox", { name: "markdown text editor" });
            const notes = PageWithExistingContent.args!.markdownText!;
            await expect(editor).toHaveValue(notes);
            await userEvent.click(editor);
            await userEvent.keyboard("{Control>}{Home}{/Control}");
            await expect(editor).toHaveProperty("selectionStart", 0);
            const datasetName = MARKDOWN_DATASET.name;
            const collectionName = MARKDOWN_COLLECTION.name;
            if (!datasetName || !collectionName) {
                throw new Error("The draggable history fixtures must have names.");
            }
            const dataset = canvas.getByText(datasetName, { exact: true });
            const collection = canvas.getByText(collectionName, { exact: true });
            const dragIntoEditor = (source: HTMLElement) => {
                const dataTransfer = new DataTransfer();
                source.dispatchEvent(new DragEvent("dragstart", { bubbles: true, cancelable: true, dataTransfer }));
                try {
                    editor.dispatchEvent(new DragEvent("dragenter", { bubbles: true, cancelable: true, dataTransfer }));
                    editor.dispatchEvent(new DragEvent("drop", { bubbles: true, cancelable: true, dataTransfer }));
                } finally {
                    source.dispatchEvent(new DragEvent("dragend", { bubbles: true, dataTransfer }));
                }
            };
            dragIntoEditor(dataset);
            const withDataset = `\n\`\`\`galaxy\nhistory_dataset_display(history_dataset_id=${MARKDOWN_DATASET.id})\n\`\`\`\n${notes}`;
            await waitFor(() => expect(editor).toHaveValue(withDataset), { timeout: 5000 });
            await userEvent.click(editor);
            await userEvent.keyboard("{Control>}{Home}{/Control}");
            await expect(editor).toHaveProperty("selectionStart", 0);
            dragIntoEditor(collection);
            const withCollection = `\n\`\`\`galaxy\nhistory_dataset_collection_display(history_dataset_collection_id=${MARKDOWN_COLLECTION.id})\n\`\`\`\n${withDataset}`;
            await waitFor(() => expect(editor).toHaveValue(withCollection), { timeout: 5000 });
        });
    },
};

/** Choosing a history dataset inserts its fenced directive at the end of existing notes. */
export const InsertsChosenDataset: Story = {
    args: PageWithExistingContent.args,
    play: async ({ canvasElement, userEvent, step }) => {
        await step("Choose a dataset and insert its directive after the existing notes", async () => {
            const canvas = within(canvasElement);
            const editor = canvas.getByRole("textbox", { name: "markdown text editor" });
            const notes = PageWithExistingContent.args!.markdownText!;
            await expect(editor).toHaveValue(notes);
            await userEvent.click(editor);
            await userEvent.keyboard("{Control>}{End}{/Control}");
            await expect(editor).toHaveProperty("selectionStart", notes.length);
            const body = within(document.body);
            await expect(body.queryByRole("dialog")).not.toBeInTheDocument();
            await userEvent.click(canvas.getByText("Dataset", { exact: true }));
            const dialog = await body.findByRole("dialog");
            const dataset = await within(dialog).findByText(
                exactly(`3: ${MARKDOWN_DATASET.name}`),
                {},
                { timeout: 5000 },
            );
            await userEvent.click(dataset);
            const inserted = `${notes}\n\`\`\`galaxy\nhistory_dataset_display(history_dataset_id=${MARKDOWN_DATASET.id})\n\`\`\`\n`;
            await waitFor(() => expect(editor).toHaveValue(inserted), { timeout: 5000 });
            await waitFor(() => expect(body.queryByRole("dialog")).not.toBeInTheDocument());
        });
    },
};
