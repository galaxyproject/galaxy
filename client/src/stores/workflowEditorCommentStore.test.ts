import { beforeEach, describe, expect, it, vi } from "vitest";

import { setupTestPinia } from "./testUtils";
import {
    type FrameWorkflowComment,
    type FreehandWorkflowComment,
    type MarkdownWorkflowComment,
    type TextWorkflowComment,
    useWorkflowCommentStore,
    type WorkflowComment,
} from "./workflowEditorCommentStore";

const freehandComment: FreehandWorkflowComment = {
    type: "freehand",
    color: "none",
    data: {
        thickness: 10,
        line: [[100, 100]],
    },
    id: 0,
    position: [100, 100],
    size: [100, 100],
};

const textComment: TextWorkflowComment = {
    type: "text",
    color: "none",
    data: {
        size: 1,
        text: "Hello World",
    },
    id: 1,
    position: [100, 200],
    size: [50, 50],
};

const markdownComment: MarkdownWorkflowComment = {
    type: "markdown",
    color: "none",
    data: {
        text: "# Hello World",
    },
    id: 2,
    position: [200, 100],
    size: [100, 100],
};

const frameComment: FrameWorkflowComment = {
    type: "frame",
    color: "none",
    data: {
        title: "My Frame",
    },
    id: 3,
    position: [0, 0],
    size: [500, 500],
};

const frameCommentTwo: FrameWorkflowComment = {
    type: "frame",
    color: "none",
    data: {
        title: "My Frame",
    },
    id: 4,
    position: [50, 50],
    size: [180, 180],
};

vi.mock("@/stores/workflowStepStore", () => ({
    useWorkflowStepStore: vi.fn(() => ({
        steps: {
            0: {
                id: 0,
                position: { left: 0, top: 0 },
            },
            1: {
                id: 1,
                position: { left: 100, top: 100 },
            },
        },
    })),
}));

vi.mock("@/stores/workflowEditorStateStore", () => ({
    useWorkflowStateStore: vi.fn(() => ({
        stepPosition: {
            0: {
                width: 200,
                height: 200,
            },
            1: {
                width: 10,
                height: 10,
            },
        },
    })),
}));

describe("workflowEditorCommentStore", () => {
    beforeEach(() => {
        setupTestPinia();
    });

    it("computes the position and size of a freehand comment", () => {
        const commentStore = useWorkflowCommentStore("mock-id");

        commentStore.createComment(freehandComment);
        commentStore.addPoint(0, [10, 1000]);
        commentStore.addPoint(0, [1000, 10]);

        expect(commentStore.comments[0]?.position).toEqual([10, 10]);
        expect(commentStore.comments[0]?.size).toEqual([990, 990]);
    });

    describe.each<{
        description: string;
        data: Record<string, unknown>;
        acceptedTypes: WorkflowComment["type"][];
    }>([
        {
            description: "text without size",
            data: { text: "Hello World" },
            acceptedTypes: ["markdown"],
        },
        {
            description: "empty data",
            data: {},
            acceptedTypes: [],
        },
        {
            description: "text with size",
            data: { text: "Hello World", size: 2 },
            acceptedTypes: ["text", "markdown"],
        },
    ])("validating $description", ({ data, acceptedTypes }) => {
        it.each([freehandComment, textComment, markdownComment, frameComment])(
            "validates the data against the $type comment requirements",
            (comment) => {
                const commentStore = useWorkflowCommentStore("mock-id");
                commentStore.addComments([freehandComment, textComment, markdownComment, frameComment]);

                const changeData = () => commentStore.changeData(comment.id, data);

                if (acceptedTypes.includes(comment.type)) {
                    expect(changeData).not.toThrow();
                } else {
                    expect(changeData).toThrow(TypeError);
                }
            },
        );
    });

    it("changes a stored comment color without mutating its input", () => {
        const commentStore = useWorkflowCommentStore("mock-id");
        const comment: TextWorkflowComment = { ...textComment, id: 0, color: "pink" };

        commentStore.addComments([comment]);
        commentStore.changeColor(0, "blue");

        expect(commentStore.comments[0]?.color).toBe("blue");
        expect(comment.color).toBe("pink");
    });

    it("clears comments and creation metadata on reset", () => {
        const commentStore = useWorkflowCommentStore("mock-id");
        commentStore.createComment({ ...textComment, id: 100 });

        expect(commentStore.comments.length).toBe(1);
        expect(commentStore.commentsRecord).not.toEqual({});
        expect(commentStore.isJustCreated(100)).toBe(true);
        expect(commentStore.highestCommentId).toBe(100);

        commentStore.$reset();

        expect(commentStore.comments.length).toBe(0);
        expect(commentStore.commentsRecord).toEqual({});
        expect(commentStore.isJustCreated(100)).toBe(false);
        expect(commentStore.highestCommentId).toBe(-1);
    });

    it("assigns comments to their innermost enclosing frame", () => {
        const commentStore = useWorkflowCommentStore("mock-id");
        commentStore.addComments([freehandComment, textComment, markdownComment, frameComment, frameCommentTwo]);

        commentStore.resolveCommentsInFrames();

        const frame = commentStore.commentsRecord[frameComment.id];
        const frameTwo = commentStore.commentsRecord[frameCommentTwo.id];

        expect(frameTwo?.child_comments?.length).toBe(1);
        expect(frameTwo?.child_comments).toContain(freehandComment.id);

        expect(frame?.child_comments?.length).toBe(3);
        expect(frame?.child_comments).toContain(frameCommentTwo.id);
        expect(frame?.child_comments).toContain(markdownComment.id);
        expect(frame?.child_comments).toContain(textComment.id);
        expect(frame?.child_comments).not.toContain(freehandComment.id);
    });

    it("assigns steps to their innermost enclosing frame", () => {
        const commentStore = useWorkflowCommentStore("mock-id");
        commentStore.addComments([frameComment, frameCommentTwo]);

        commentStore.resolveStepsInFrames();

        const frame = commentStore.commentsRecord[frameComment.id];
        const frameTwo = commentStore.commentsRecord[frameCommentTwo.id];

        expect(frame?.child_steps).toContain(0);
        expect(frameTwo?.child_steps).toContain(1);

        expect(frame?.child_steps).not.toContain(1);
        expect(frameTwo?.child_steps).not.toContain(0);
    });

    it("tracks selected comments through selection, removal, toggling, and clearing", () => {
        const commentStore = useWorkflowCommentStore("mock-id");
        commentStore.addComments([freehandComment, textComment, markdownComment, frameComment, frameCommentTwo]);

        commentStore.setCommentMultiSelected(freehandComment.id, true);
        commentStore.setCommentMultiSelected(markdownComment.id, true);

        expect(commentStore.getCommentMultiSelected(freehandComment.id)).toBe(true);
        expect(commentStore.getCommentMultiSelected(textComment.id)).toBe(false);
        expect(commentStore.getCommentMultiSelected(markdownComment.id)).toBe(true);

        expect(commentStore.multiSelectedCommentIds).toEqual([freehandComment.id, markdownComment.id]);

        commentStore.setCommentMultiSelected(markdownComment.id, false);

        expect(commentStore.getCommentMultiSelected(markdownComment.id)).toBe(false);
        expect(commentStore.multiSelectedCommentIds).toEqual([freehandComment.id]);

        commentStore.toggleCommentMultiSelected(textComment.id);
        expect(commentStore.getCommentMultiSelected(textComment.id)).toBe(true);

        commentStore.clearMultiSelectedComments();

        expect(commentStore.multiSelectedCommentIds).toEqual([]);
    });
});
