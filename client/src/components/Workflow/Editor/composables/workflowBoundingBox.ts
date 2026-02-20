import { useWorkflowStores } from "@/composables/workflowStores";

import { AxisAlignedBoundingBox, type WorkflowTransform } from "../modules/geometry";

export interface BoundingBoxBounds {
    minX: number;
    minY: number;
}

export interface CapturedState {
    transform: WorkflowTransform;
    bounds: BoundingBoxBounds;
}

export function useWorkflowBoundingBox(workflowId?: string) {
    const { stepStore, stateStore, commentStore } = useWorkflowStores(workflowId);

    const getWorkflowBoundingBox = () => {
        const aabb = new AxisAlignedBoundingBox();

        Object.values(stepStore.steps).forEach((step) => {
            const rect = stateStore.stepPosition[step.id];

            if (rect) {
                aabb.fitRectangle({
                    x: step.position!.left,
                    y: step.position!.top,
                    width: rect.width,
                    height: rect.height,
                });
            }
        });

        commentStore.comments.forEach((comment) => {
            aabb.fitRectangle({
                x: comment.position[0],
                y: comment.position[1],
                width: comment.size[0],
                height: comment.size[1],
            });
        });

        return aabb;
    };

    /**
     * Captures the current transform and bounding box bounds.
     * Call this before a workflow reload/refactor to preserve viewport position.
     */
    function captureTransformAndBounds(transform: WorkflowTransform): CapturedState {
        const boundingBox = getWorkflowBoundingBox();
        return {
            transform: { ...transform },
            bounds: { minX: boundingBox.x, minY: boundingBox.y },
        };
    }

    /**
     * Calculates the adjusted transform to compensate for coordinate shifts
     * that may be computed by the backend when a workflow step order/positioning
     * changes.
     *
     * @param transformBefore The transform captured before reload
     * @param boundsBefore The bounds captured before reload
     * @returns The adjusted transform to apply to `WorkflowGraph`
     */
    function calculateAdjustedTransform(
        transformBefore: WorkflowTransform,
        boundsBefore: BoundingBoxBounds,
    ): WorkflowTransform {
        const newBoundingBox = getWorkflowBoundingBox();
        const newBounds = { minX: newBoundingBox.x, minY: newBoundingBox.y };

        // If either bounding box is empty (no steps/comments), skip adjustment
        // to avoid NaN from Infinity - Infinity calculations
        if (
            !Number.isFinite(boundsBefore.minX) ||
            !Number.isFinite(boundsBefore.minY) ||
            !Number.isFinite(newBounds.minX) ||
            !Number.isFinite(newBounds.minY)
        ) {
            return { ...transformBefore };
        }

        const offsetX = boundsBefore.minX - newBounds.minX;
        const offsetY = boundsBefore.minY - newBounds.minY;

        // Scale the offset by the current zoom level since transform is in viewport coordinates
        const scaledOffsetX = offsetX * transformBefore.k;
        const scaledOffsetY = offsetY * transformBefore.k;

        return {
            x: transformBefore.x + scaledOffsetX,
            y: transformBefore.y + scaledOffsetY,
            k: transformBefore.k,
        };
    }

    return {
        getWorkflowBoundingBox,
        captureTransformAndBounds,
        calculateAdjustedTransform,
    };
}
