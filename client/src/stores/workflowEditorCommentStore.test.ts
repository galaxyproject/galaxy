import { createPinia, setActivePinia } from "pinia";

import {
    FrameWorkflowComment,
    type FreehandWorkflowComment,
    MarkdownWorkflowComment,
    type TextWorkflowComment,
    useWorkflowCommentStore,
} from "./workflowEditorCommentStore";

const freehandComment: FreehandWorkflowComment = {
    type: "freehand",
    colour: "none",
    data: {
        thickness: 10,
        line: [[100, 100]],
    },
    id: 0,
    position: [100, 100],
    size: [0, 0],
};

const textComment: TextWorkflowComment = {
    type: "text",
    colour: "none",
    data: {
        size: 1,
        text: "Hello World",
    },
    id: 1,
    position: [100, 100],
    size: [0, 0],
};

const markdownComment: MarkdownWorkflowComment = {
    type: "markdown",
    colour: "none",
    data: {
        text: "# Hello World",
    },
    id: 2,
    position: [100, 100],
    size: [0, 0],
};

const frameComment: FrameWorkflowComment = {
    type: "frame",
    colour: "none",
    data: {
        title: "My Frame",
    },
    id: 3,
    position: [100, 100],
    size: [0, 0],
};

describe("workflowEditorCommentStore", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    it("computes the position and size of a freehand comment", () => {
        const commentStore = useWorkflowCommentStore("mock-id");

        commentStore.createComment(freehandComment);
        commentStore.addPoint(0, [10, 1000]);
        commentStore.addPoint(0, [1000, 10]);

        expect(commentStore.comments[0]?.position).toEqual([10, 10]);
        expect(commentStore.comments[0]?.size).toEqual([990, 990]);
    });

    it("validates comment data", () => {
        const commentStore = useWorkflowCommentStore("mock-id");

        commentStore.addComments([freehandComment, textComment, markdownComment, frameComment]);

        const testData = {
            text: "Hello World",
        };

        expect(() => commentStore.changeData(0, testData)).toThrow(TypeError);
        expect(() => commentStore.changeData(1, testData)).toThrow(TypeError);
        expect(() => commentStore.changeData(2, testData)).not.toThrow();
        expect(() => commentStore.changeData(3, testData)).toThrow(TypeError);

        expect(() => commentStore.changeData(0, {})).toThrow(TypeError);
        expect(() => commentStore.changeData(1, {})).toThrow(TypeError);
        expect(() => commentStore.changeData(2, {})).toThrow(TypeError);
        expect(() => commentStore.changeData(3, {})).toThrow(TypeError);

        const duckTypedTestData = {
            text: "Hello World",
            size: 2,
        };

        expect(() => commentStore.changeData(0, duckTypedTestData)).toThrow(TypeError);
        expect(() => commentStore.changeData(1, duckTypedTestData)).not.toThrow();
        expect(() => commentStore.changeData(2, duckTypedTestData)).not.toThrow();
        expect(() => commentStore.changeData(3, duckTypedTestData)).toThrow(TypeError);
    });

    it("does not mutate input data", () => {
        const commentStore = useWorkflowCommentStore("mock-id");
        const comment: TextWorkflowComment = { ...textComment, id: 0, colour: "pink" };

        commentStore.addComments([comment]);
        commentStore.changeColour(0, "blue");

        expect(commentStore.comments[0]?.colour).toBe("blue");
        expect(comment.colour).toBe("pink");
    });

    it("implements reset", () => {
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
});
