import { defineStore } from "pinia";
import { computed, ref, set } from "vue";

import type { Colour } from "@/components/Workflow/Editor/Comments/colours";

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
}

export interface FrameWorkflowComment extends BaseWorkflowComment {
    type: "frame";
}

export interface MarkdownWorkflowComment extends BaseWorkflowComment {
    type: "markdown";
}

export interface FreehandWorkflowComment extends BaseWorkflowComment {
    type: "freehand";
}

export type WorkflowComment =
    | TextWorkflowComment
    | FrameWorkflowComment
    | MarkdownWorkflowComment
    | FreehandWorkflowComment;

export const useWorkflowCommentStore = (workflowId: string) => {
    return defineStore(`workflowCommentStore${workflowId}`, () => {
        const commentsRecord = ref<Record<number, WorkflowComment>>({});

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

        return {
            commentsRecord,
            comments,
            addComments,
            highestCommentId,
            $reset,
        };
    })();
};
