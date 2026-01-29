import { useWorkflowStores } from "@/composables/workflowStores";

import { AxisAlignedBoundingBox } from "../modules/geometry";

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

    return {
        getWorkflowBoundingBox,
    };
}
