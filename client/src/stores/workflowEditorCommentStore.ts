import { defineStore } from "pinia";
import { ref } from "vue";

export type WorkflowCommentColour = string;

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

        function $reset() {
            commentsRecord.value = {};
        }

        return {
            $reset,
        };
    })();
};
