import { defineStore } from "pinia";
import { computed, del, ref, set } from "vue";

import type { Colour } from "@/components/Workflow/Editor/Comments/colours";
import { vecReduceFigures, Vector } from "@/components/Workflow/Editor/modules/geometry";
import { assertDefined } from "@/utils/assertions";
import { hasKeys, match } from "@/utils/utils";

export type WorkflowCommentColour = Colour | "none";

export interface BaseWorkflowComment {
    id: number;
    type: string;
    colour: WorkflowCommentColour;
    position: [number, number];
    size: [number, number];
    data: unknown;
}

export interface TextWorkflowComment extends BaseWorkflowComment {
    type: "text";
    data: {
        bold?: true;
        italic?: true;
        size: number;
        text: string;
    };
}

export interface FrameWorkflowComment extends BaseWorkflowComment {
    type: "frame";
    data: {
        title: string;
    };
}

export interface MarkdownWorkflowComment extends BaseWorkflowComment {
    type: "markdown";
    data: {
        text: string;
    };
}

export interface FreehandWorkflowComment extends BaseWorkflowComment {
    type: "freehand";
    data: {
        thickness: number;
        line: Vector[];
    };
}

export type WorkflowComment =
    | TextWorkflowComment
    | FrameWorkflowComment
    | MarkdownWorkflowComment
    | FreehandWorkflowComment;

interface CommentsMetadata {
    justCreated?: boolean;
}

function assertCommentDataValid(
    annotationType: WorkflowComment["type"],
    annotationData: unknown
): asserts annotationData is WorkflowComment["data"] {
    const valid = match(annotationType, {
        text: () => hasKeys(annotationData, ["text", "size"]),
        markdown: () => hasKeys(annotationData, ["text"]),
        frame: () => hasKeys(annotationData, ["title"]),
        freehand: () => hasKeys(annotationData, ["thickness", "line"]),
    });

    if (!valid) {
        throw new TypeError(
            `Object "${annotationData}" is not a valid data object for an ${annotationType} annotation`
        );
    }
}

export const useWorkflowCommentStore = (workflowId: string) => {
    return defineStore(`workflowCommentStore${workflowId}`, () => {
        const commentsRecord = ref<Record<number, WorkflowComment>>({});
        const localCommentsMetadata = ref<Record<number, CommentsMetadata>>({});

        const comments = computed(() => Object.values(commentsRecord.value));

        function $reset() {
            commentsRecord.value = {};
        }

        const addComments = (commentsArray: WorkflowComment[], defaultPosition: [number, number] = [0, 0]) => {
            commentsArray.forEach((comment) => {
                const newComment = structuredClone(comment);
                newComment.position[0] += defaultPosition[0];
                newComment.position[1] += defaultPosition[1];

                set(commentsRecord.value, newComment.id, newComment);
            });
        };

        const highestCommentId = computed(() => comments.value[comments.value.length - 1]?.id ?? -1);

        const isJustCreated = computed(() => (id: number) => localCommentsMetadata.value[id]?.justCreated ?? false);

        const getComment = computed(() => (id: number) => {
            const comment = commentsRecord.value[id];
            assertDefined(comment);
            return comment;
        });

        function changePosition(id: number, position: [number, number]) {
            const comment = getComment.value(id);
            set(comment, "position", vecReduceFigures(position));
        }

        function changeSize(id: number, size: [number, number]) {
            const comment = getComment.value(id);
            set(comment, "size", vecReduceFigures(size));
        }

        function changeData(id: number, data: unknown) {
            const comment = getComment.value(id);
            assertCommentDataValid(comment.type, data);
            set(comment, "data", data);
        }

        function changeColour(id: number, colour: WorkflowCommentColour) {
            const comment = getComment.value(id);
            set(comment, "colour", colour);
        }

        function deleteComment(id: number) {
            del(commentsRecord.value, id);
        }

        return {
            commentsRecord,
            comments,
            addComments,
            highestCommentId,
            isJustCreated,
            changePosition,
            changeSize,
            changeData,
            changeColour,
            deleteComment,
            $reset,
        };
    })();
};
