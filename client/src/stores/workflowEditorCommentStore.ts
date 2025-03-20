import { computed, del, ref, set } from "vue";

import { type Color } from "@/components/Workflow/Editor/Comments/colors";
import {
    AxisAlignedBoundingBox,
    type Rectangle,
    vecAdd,
    vecMax,
    vecMin,
    vecReduceFigures,
    vecSubtract,
    type Vector,
} from "@/components/Workflow/Editor/modules/geometry";
import { assertDefined } from "@/utils/assertions";
import { hasKeys, match } from "@/utils/utils";

import { defineScopedStore } from "./scopedStore";
import { useWorkflowStateStore } from "./workflowEditorStateStore";
import { type Step, useWorkflowStepStore } from "./workflowStepStore";

export type WorkflowCommentColor = Color | "none";

export interface BaseWorkflowComment {
    id: number;
    type: string;
    color: WorkflowCommentColor;
    position: [number, number];
    size: [number, number];
    data: unknown;
    child_comments?: number[];
    child_steps?: number[];
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

export type WorkflowCommentType = WorkflowComment["type"];

interface CommentsMetadata {
    justCreated?: boolean;
    multiSelected?: boolean;
}

function assertCommentDataValid(
    commentType: WorkflowComment["type"],
    commentData: unknown
): asserts commentData is WorkflowComment["data"] {
    const valid = match(commentType, {
        text: () => hasKeys(commentData, ["text", "size"]),
        markdown: () => hasKeys(commentData, ["text"]),
        frame: () => hasKeys(commentData, ["title"]),
        freehand: () => hasKeys(commentData, ["thickness", "line"]),
    });

    if (!valid) {
        throw new TypeError(`Object "${commentData}" is not a valid data object for an ${commentType} comment`);
    }
}

export type WorkflowCommentStore = ReturnType<typeof useWorkflowCommentStore>;

export const useWorkflowCommentStore = defineScopedStore("workflowCommentStore", (workflowId) => {
    const commentsRecord = ref<Record<number, WorkflowComment>>({});
    const localCommentsMetadata = ref<Record<number, CommentsMetadata>>({});

    const comments = computed(() => Object.values(commentsRecord.value));

    function $reset() {
        commentsRecord.value = {};
        localCommentsMetadata.value = {};
    }

    const addComments = (
        commentsArray: WorkflowComment[],
        defaultPosition: [number, number] = [0, 0],
        select = false
    ) => {
        commentsArray.forEach((comment) => {
            const newComment = structuredClone(comment);
            newComment.position[0] += defaultPosition[0];
            newComment.position[1] += defaultPosition[1];

            set(commentsRecord.value, newComment.id, newComment);

            if (select) {
                setCommentMultiSelected(newComment.id, true);
            }
        });
    };

    const highestCommentId = computed(() => comments.value[comments.value.length - 1]?.id ?? -1);

    const isJustCreated = computed(() => (id: number) => localCommentsMetadata.value[id]?.justCreated ?? false);

    const getComment = computed(() => (id: number) => {
        const comment = commentsRecord.value[id];
        assertDefined(comment);
        return comment;
    });

    const multiSelectedCommentIds = computed(() =>
        Object.entries(localCommentsMetadata.value)
            .filter(([_id, meta]) => meta.multiSelected)
            .map(([id]) => parseInt(id))
    );

    const getCommentMultiSelected = computed(() => (id: number) => {
        return Boolean(localCommentsMetadata.value[id]?.multiSelected);
    });

    function setCommentMultiSelected(id: number, selected: boolean) {
        const meta = localCommentsMetadata.value[id];

        if (meta) {
            set(meta, "multiSelected", selected);
        } else {
            set(localCommentsMetadata.value, id, { multiSelected: selected });
        }
    }

    function toggleCommentMultiSelected(id: number) {
        setCommentMultiSelected(id, !getCommentMultiSelected.value(id));
    }

    function clearMultiSelectedComments() {
        Object.values(localCommentsMetadata.value).forEach((meta) => (meta.multiSelected = false));
    }

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

    function changeColor(id: number, color: WorkflowCommentColor) {
        const comment = getComment.value(id);
        set(comment, "color", color);
    }

    function addPoint(id: number, point: [number, number]) {
        const comment = getComment.value(id);
        if (!(comment.type === "freehand")) {
            throw new Error("Can only add points to freehand comment");
        }

        comment.data.line.push(point);

        comment.size = vecMax(comment.size, vecSubtract(point, comment.position));

        const prevPosition = comment.position;
        comment.position = vecMin(comment.position, point);

        const diff = vecSubtract(prevPosition, comment.position);
        comment.size = vecAdd(comment.size, diff);
    }

    function deleteComment(id: number) {
        del(commentsRecord.value, id);
        del(localCommentsMetadata.value, id);
    }

    /**
     * Adds a single comment. Sets the `userCreated` flag.
     * Meant to be used when a user adds an comment.
     * @param comment
     */
    function createComment(comment: BaseWorkflowComment) {
        markJustCreated(comment.id);
        addComments([comment as WorkflowComment]);
    }

    function markJustCreated(id: number) {
        set(localCommentsMetadata.value, id, { justCreated: true });
    }

    function clearJustCreated(id: number) {
        const metadata = localCommentsMetadata.value[id];

        if (metadata) {
            del(metadata, "justCreated");
        }
    }

    function deleteFreehandComments() {
        Object.values(commentsRecord.value).forEach((comment) => {
            if (comment.type === "freehand") {
                deleteComment(comment.id);
            }
        });
    }

    function commentToRectangle(comment: WorkflowComment): Rectangle {
        return {
            x: comment.position[0],
            y: comment.position[1],
            width: comment.size[0],
            height: comment.size[1],
        };
    }

    /** Calculates which comments are within frames and attaches that information to the parent comments */
    function resolveCommentsInFrames() {
        // reverse to give frames on top of other frames higher precedence
        const frameComments = comments.value.filter((comment) => comment.type === "frame").reverse();
        let candidates = [...comments.value];

        frameComments.forEach((frame) => {
            const bounds = new AxisAlignedBoundingBox();
            bounds.fitRectangle(commentToRectangle(frame));
            frame.child_comments = [];

            // remove when matched, so each comment can only be linked to one frame
            candidates = candidates.flatMap((comment) => {
                const rect: Rectangle = commentToRectangle(comment);

                if (comment !== frame && bounds.contains(rect)) {
                    // push id and remove from candidates when in bounds
                    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
                    frame.child_comments!.push(comment.id);
                    return [];
                } else {
                    // otherwise do nothing and keep in list
                    return [comment];
                }
            });
        });
    }

    const stateStore = useWorkflowStateStore(workflowId);

    function stepToRectangle(step: Step): Rectangle | null {
        const rect = stateStore.stepPosition[step.id];

        if (rect && step.position) {
            return {
                x: step.position.left,
                y: step.position.top,
                width: rect.width,
                height: rect.height,
            };
        } else {
            return null;
        }
    }

    const stepStore = useWorkflowStepStore(workflowId);

    /** Calculates which steps are within frames and attaches that information to the parent comments */
    function resolveStepsInFrames() {
        // reverse to give frames on top of other frames higher precedence
        const frameComments = comments.value.filter((comment) => comment.type === "frame").reverse();
        let candidates = [...Object.values(stepStore.steps)];

        frameComments.forEach((frame) => {
            const bounds = new AxisAlignedBoundingBox();
            bounds.fitRectangle(commentToRectangle(frame));
            frame.child_steps = [];

            // remove when matched, so each step can only be linked to one frame
            candidates = candidates.flatMap((step) => {
                const rect = stepToRectangle(step);

                if (rect && bounds.contains(rect)) {
                    // push id and remove from candidates when in bounds
                    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
                    frame.child_steps!.push(step.id);
                    return [];
                } else {
                    // otherwise do nothing and keep in list
                    return [step];
                }
            });
        });
    }

    return {
        commentsRecord,
        comments,
        localCommentsMetadata,
        addComments,
        highestCommentId,
        isJustCreated,
        multiSelectedCommentIds,
        getCommentMultiSelected,
        setCommentMultiSelected,
        toggleCommentMultiSelected,
        clearMultiSelectedComments,
        changePosition,
        changeSize,
        changeData,
        changeColor,
        addPoint,
        deleteComment,
        createComment,
        clearJustCreated,
        deleteFreehandComments,
        resolveCommentsInFrames,
        resolveStepsInFrames,
        $reset,
    };
});
