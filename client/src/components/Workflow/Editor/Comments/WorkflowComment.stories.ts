import type { Decorator, Meta, StoryObj } from "@storybook/vue3-vite";
import { zoomIdentity } from "d3-zoom";
import { expect } from "storybook/test";
import { computed, h, markRaw, provide, ref } from "vue";

import { useWorkflowCommentStore } from "@/stores/workflowEditorCommentStore";

import { mockOffset, withWorkflowStores } from "../test_fixtures";
import { COMMENTS_WORKFLOW_ID } from "./test_fixtures";

import WorkflowComment from "./WorkflowComment.vue";

/** The editor canvas: comments are placed inside it and drag with its zoom transform. */
const withCanvas: Decorator = (story) => ({
    setup() {
        provide("transform", ref(zoomIdentity));
        return () => h("div", { style: { position: "relative", height: "260px" } }, [h(story())]);
    },
});

const meta = {
    title: "Workflow/Editor/Comments/WorkflowComment",
    component: WorkflowComment,
    decorators: [withCanvas, withWorkflowStores(COMMENTS_WORKFLOW_ID)],
    /** As the editor's graph does, show the comment from the workflow's store, so edits show and a deleted one goes. */
    render: (args) => ({
        setup() {
            const commentStore = useWorkflowCommentStore(COMMENTS_WORKFLOW_ID);
            commentStore.addComments([args.comment]);
            const comment = computed(() => commentStore.comments.find(({ id }) => id === args.comment.id));
            return () => (comment.value ? h(WorkflowComment, { ...args, comment: comment.value }) : null);
        },
    }),
    args: {
        scale: 1,
        rootOffset: markRaw(mockOffset),
        comment: {
            id: 0,
            type: "text",
            color: "none",
            position: [16, 16],
            size: [240, 72],
            data: { size: 1, text: "Trim adapters before mapping<br>Check the fastp report first" },
        },
    },
    // The render seeds the store once, so editing the comment in Controls would change nothing.
    argTypes: { rootOffset: { control: false }, comment: { control: false } },
} satisfies Meta<typeof WorkflowComment>;

export default meta;
type Story = StoryObj<typeof meta>;

/** A plain text note, one line break kept. */
export const TextNote: Story = {
    play: async ({ canvas, step }) => {
        await step("Read the plain text note", async () => {
            const note = await canvas.findByText(/Trim adapters before mapping/);
            await expect(note).toBeVisible();
            await expect(note).toHaveTextContent(/^Trim adapters before mapping\s*Check the fastp report first$/);
        });
    },
};

/** A Markdown note: a link opens in a new tab, and raw HTML shows as text. */
export const MarkdownNote: Story = {
    args: {
        comment: {
            id: 1,
            type: "markdown",
            color: "none",
            position: [16, 16],
            size: [300, 120],
            data: {
                text: "Reads are trimmed with **fastp**. Read the [RNA-seq tutorial](https://training.galaxyproject.org/training-material/topics/transcriptomics/) <b>before</b> changing its settings.",
            },
        },
    },
    play: async ({ canvas, step }) => {
        await step("Read the Markdown note with a tutorial link", async () => {
            const link = await canvas.findByRole("link", { name: "RNA-seq tutorial" });
            await expect(link).toBeVisible();
            await expect(link).toHaveAttribute(
                "href",
                "https://training.galaxyproject.org/training-material/topics/transcriptomics/",
            );
            await expect(link).toHaveAttribute("target", "_blank");
            const tool = canvas.getByText("fastp", { exact: true });
            await expect(tool).toBeVisible();
            await expect(tool.tagName).toBe("STRONG");
            await expect(canvas.getByRole("paragraph")).toHaveTextContent(
                /^Reads are trimmed with fastp\. Read the RNA-seq tutorial <b>before<\/b> changing its settings\.$/,
            );
            await expect(canvas.queryByText("before", { exact: true })).not.toBeInTheDocument();
        });
    },
};

/** A colored frame grouping the steps under its title. */
export const ColoredFrame: Story = {
    args: {
        comment: {
            id: 2,
            type: "frame",
            color: "blue",
            position: [16, 16],
            size: [360, 220],
            data: { title: "Quality control" },
        },
    },
};

/** A freehand stroke as the editor saves it: points relative to its top-left corner. */
export const FreehandDrawing: Story = {
    args: {
        comment: {
            id: 3,
            type: "freehand",
            color: "red",
            position: [16, 16],
            size: [170, 60],
            data: {
                thickness: 4,
                line: [
                    [0, 60],
                    [50, 10],
                    [100, 40],
                    [170, 0],
                ],
            },
        },
    },
};
