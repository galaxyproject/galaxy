import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentHistory } from "@tests/test-data/currentHistory";
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
