import simplify from "simplify-js";
import { watch } from "vue";

import type { BaseWorkflowComment, WorkflowCommentStore } from "@/stores/workflowEditorCommentStore";
import { type WorkflowEditorToolbarStore } from "@/stores/workflowEditorToolbarStore";
import { assertDefined } from "@/utils/assertions";
import { match } from "@/utils/utils";

import { vecMax, vecMin, vecReduceFigures, vecSnap, vecSubtract, type Vector } from "../modules/geometry";

export function useToolLogic(toolbarStore: WorkflowEditorToolbarStore, commentStore: WorkflowCommentStore) {
    let comment: BaseWorkflowComment | null = null;
    let start: Vector | null = null;

    const { commentOptions } = toolbarStore;

    watch(
        () => toolbarStore.currentTool,
        () => {
            if (comment?.type === "freehand") {
                finalizeFreehandComment(comment);
            } else {
                comment = null;
            }
        }
    );

    toolbarStore.onInputCatcherEvent("pointerdown", ({ position }) => {
        start = position;

        if (toolbarStore.currentTool === "freehandEraser") {
            return;
        }

        if (comment?.type === "freehand" || !comment) {
            const baseComment = {
                id: commentStore.highestCommentId + 1,
                position: start,
                size: [0, 0] as [number, number],
                color: commentOptions.color,
            };

            comment = match(toolbarStore.currentTool, {
                textComment: () => ({
                    ...baseComment,
                    type: "text",
                    data: {
                        size: commentOptions.textSize,
                        text: "Enter Text",
                        bold: commentOptions.bold || undefined,
                        italic: commentOptions.italic || undefined,
                    } as BaseWorkflowComment["data"],
                }),
                markdownComment: () => ({
                    ...baseComment,
                    type: "markdown",
                    data: {
                        text: "*Enter Text*",
                    },
                }),
                frameComment: () => ({
                    ...baseComment,
                    type: "frame",
                    data: {
                        title: "Frame",
                    },
                }),
                freehandComment: () => ({
                    ...baseComment,
                    type: "freehand",
                    data: {
                        thickness: commentOptions.lineThickness,
                        line: [position],
                    },
                }),
                pointer: () => {
                    throw new Error("Tool logic should not be active when pointer tool is selected");
                },
            });

            commentStore.createComment(comment);
        }
    });

    toolbarStore.onInputCatcherEvent("pointermove", ({ position }) => {
        if (toolbarStore.currentTool === "freehandEraser") {
            return;
        }

        if (comment && start) {
            if (comment.type === "freehand") {
                commentStore.addPoint(comment.id, position);
            } else {
                positionComment(start, position, comment);
            }
        }
    });

    toolbarStore.onInputCatcherEvent("pointerup", () => {
        if (toolbarStore.currentTool === "freehandEraser") {
            return;
        } else if (comment?.type === "freehand") {
            finalizeFreehandComment(comment);
        } else if (toolbarStore.currentTool !== "freehandComment") {
            toolbarStore.currentTool = "pointer";
        }

        comment = null;
    });

    toolbarStore.onInputCatcherEvent("pointerleave", () => {
        if (comment?.type === "freehand") {
            finalizeFreehandComment(comment);
            comment = null;
        }
    });

    toolbarStore.onInputCatcherEvent("temporarilyDisabled", () => {
        if (comment?.type === "freehand") {
            finalizeFreehandComment(comment);
            comment = null;
        }
    });

    const finalizeFreehandComment = (comment: BaseWorkflowComment) => {
        const freehandComment = commentStore.commentsRecord[comment.id];
        assertDefined(freehandComment);
        if (freehandComment.type !== "freehand") {
            throw new Error("Comment is not of type freehandComment");
        }

        // smooth
        const xyLine = freehandComment.data.line.map((point) => ({ x: point[0], y: point[1] }));
        const simpleLine = simplify(xyLine, commentOptions.smoothing).map((point) => [
            point.x,
            point.y,
        ]) as Array<Vector>;

        // normalize
        const normalized = simpleLine.map((p) => vecSubtract(p, freehandComment.position));

        // reduce significant figures
        const line = normalized.map((p) => vecReduceFigures(p) as Vector);

        commentStore.changeData(freehandComment.id, { ...freehandComment.data, line });
        commentStore.changePosition(freehandComment.id, vecReduceFigures(freehandComment.position));
        commentStore.changeSize(freehandComment.id, vecReduceFigures(freehandComment.size));
        commentStore.clearJustCreated(freehandComment.id);
    };

    const positionComment = (pointA: Vector, pointB: Vector, comment: BaseWorkflowComment) => {
        if (toolbarStore.snapActive) {
            pointA = vecSnap(pointA, toolbarStore.snapDistance);
            pointB = vecSnap(pointB, toolbarStore.snapDistance);
        }

        const pointMin = vecMin(pointA, pointB);
        const pointMax = vecMax(pointA, pointB);

        const position = pointMin;
        const size = vecSubtract(pointMax, pointMin);

        commentStore.changePosition(comment.id, position);
        commentStore.changeSize(comment.id, size);
    };
}
