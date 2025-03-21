import simplify from "simplify-js";
import { ref, watch } from "vue";

import { useWorkflowStores } from "@/composables/workflowStores";
import { type BaseWorkflowComment } from "@/stores/workflowEditorCommentStore";
import { assertDefined } from "@/utils/assertions";
import { match } from "@/utils/utils";

import { AddCommentAction } from "../Actions/commentActions";
import { AddToSelectionAction, RemoveFromSelectionAction } from "../Actions/workflowActions";
import {
    AxisAlignedBoundingBox,
    vecMax,
    vecMin,
    vecReduceFigures,
    vecSnap,
    vecSubtract,
    type Vector,
} from "../modules/geometry";

export function useToolLogic() {
    const comment = ref<BaseWorkflowComment | null>(null);
    let start: Vector | null = null;

    const { toolbarStore, commentStore, stepStore, stateStore, undoRedoStore } = useWorkflowStores();
    const { commentOptions } = toolbarStore;

    watch(
        () => toolbarStore.currentTool,
        () => {
            if (comment.value?.type === "freehand") {
                finalizeFreehandComment(comment.value);
            } else {
                comment.value = null;
            }
        }
    );

    watch(
        () => comment.value,
        (newComment, oldComment) => {
            if (newComment === null && oldComment !== null) {
                const comment = commentStore.commentsRecord[oldComment.id];
                assertDefined(comment);
                undoRedoStore.applyAction(new AddCommentAction(commentStore, comment));
            }

            toolbarStore.resetBoxSelect();
        }
    );

    toolbarStore.onInputCatcherEvent("pointerdown", ({ position }) => {
        start = position;

        if (toolbarStore.currentTool === "freehandEraser") {
            return;
        }

        if (toolbarStore.currentTool === "boxSelect") {
            return;
        }

        if (comment.value?.type === "freehand" || !comment.value) {
            const baseComment = {
                id: commentStore.highestCommentId + 1,
                position: start,
                size: [0, 0] as [number, number],
                color: commentOptions.color,
            };

            comment.value = match(toolbarStore.currentTool, {
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
                    throw new Error("选择指针工具时，工具逻辑不应处于活动状态");
                },
            });

            commentStore.createComment(comment.value);
        }
    });

    toolbarStore.onInputCatcherEvent("pointermove", ({ position }) => {
        if (toolbarStore.currentTool === "freehandEraser") {
            return;
        }

        if (toolbarStore.currentTool === "boxSelect" && start) {
            const [boxPosition, boxSize] = pointsToPositionSize(start, position);
            toolbarStore.boxSelectRect = {
                x: boxPosition[0],
                y: boxPosition[1],
                width: boxSize[0],
                height: boxSize[1],
            };
            return;
        }

        if (comment.value && start) {
            if (comment.value.type === "freehand") {
                commentStore.addPoint(comment.value.id, position);
            } else {
                positionComment(start, position, comment.value);
            }
        }
    });

    toolbarStore.onInputCatcherEvent("pointerup", () => {
        if (toolbarStore.currentTool === "freehandEraser") {
            return;
        } else if (comment.value?.type === "freehand") {
            finalizeFreehandComment(comment.value);
        } else if (toolbarStore.currentTool === "boxSelect") {
            finalizeBoxSelect();
        } else if (toolbarStore.currentTool !== "freehandComment") {
            toolbarStore.currentTool = "pointer";
        }

        comment.value = null;
        start = null;
    });

    toolbarStore.onInputCatcherEvent("pointerleave", () => {
        if (comment.value?.type === "freehand") {
            finalizeFreehandComment(comment.value);
            comment.value = null;
        }
    });

    toolbarStore.onInputCatcherEvent("temporarilyDisabled", () => {
        if (comment.value?.type === "freehand") {
            finalizeFreehandComment(comment.value);
            comment.value = null;
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

    function finalizeBoxSelect() {
        const boxAABB = new AxisAlignedBoundingBox();
        boxAABB.fitRectangle(toolbarStore.boxSelectRect);

        const commentsInRect = commentStore.comments.filter((comment) =>
            boxAABB.contains({
                x: comment.position[0],
                y: comment.position[1],
                width: comment.size[0],
                height: comment.size[1],
            })
        );

        const stepsInRect = Object.values(stepStore.steps).filter((step) => {
            const rect = stateStore.stepPosition[step.id];

            if (rect && step.position) {
                const stepRect = {
                    x: step.position.left,
                    y: step.position.top,
                    width: rect.width,
                    height: rect.height,
                };

                return boxAABB.contains(stepRect);
            } else {
                return false;
            }
        });

        toolbarStore.resetBoxSelect();

        if (commentsInRect.length > 0 || stepsInRect.length > 0) {
            const changedSelection = {
                comments: commentsInRect.map((comment) => comment.id),
                steps: stepsInRect.map((step) => step.id),
            };

            if (toolbarStore.boxSelectMode === "add") {
                undoRedoStore.applyAction(new AddToSelectionAction(commentStore, stateStore, changedSelection));
            } else {
                undoRedoStore.applyAction(new RemoveFromSelectionAction(commentStore, stateStore, changedSelection));
            }
        }
    }

    const positionComment = (pointA: Vector, pointB: Vector, comment: BaseWorkflowComment) => {
        if (toolbarStore.snapActive) {
            pointA = vecSnap(pointA, toolbarStore.snapDistance);
            pointB = vecSnap(pointB, toolbarStore.snapDistance);
        }

        const [position, size] = pointsToPositionSize(pointA, pointB);

        commentStore.changePosition(comment.id, position);
        commentStore.changeSize(comment.id, size);
    };

    function pointsToPositionSize(pointA: Vector, pointB: Vector): [Vector, Vector] {
        const pointMin = vecMin(pointA, pointB);
        const pointMax = vecMax(pointA, pointB);

        const position = pointMin;
        const size = vecSubtract(pointMax, pointMin);

        return [position, size];
    }
}
