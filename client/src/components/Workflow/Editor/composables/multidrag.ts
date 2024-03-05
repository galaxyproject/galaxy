import { useWorkflowStores } from "@/composables/workflowStores";
import type { WorkflowComment } from "@/stores/workflowEditorCommentStore";
import type { Step } from "@/stores/workflowStepStore";

export function useMultidrag() {
    type StepWithPosition = Step & { position: NonNullable<Step["position"]> };

    let multidragSteps: StepWithPosition[] = [];
    let multidragComments: WorkflowComment[] = [];
    const stepStartOffsets = new Map<number, [number, number]>();
    const commentStartOffsets = new Map<number, [number, number]>();

    const { stepStore, commentStore } = useWorkflowStores();

    function multidragStart(
        startPosition: { x: number; y: number },
        stepsToDrag: StepWithPosition[],
        commentsToDrag: WorkflowComment[]
    ) {
        multidragSteps = stepsToDrag;
        multidragComments = commentsToDrag;

        multidragSteps.forEach((step) => {
            stepStartOffsets.set(step.id, [step.position.left - startPosition.x, step.position.top - startPosition.y]);
        });

        multidragComments.forEach((comment) => {
            commentStartOffsets.set(comment.id, [
                comment.position[0] - startPosition.x,
                comment.position[1] - startPosition.y,
            ]);
        });
    }

    function multidragEnd() {
        multidragSteps = [];
        multidragComments = [];
        stepStartOffsets.clear();
        commentStartOffsets.clear();
    }

    function multidragMove(position: { x: number; y: number }) {
        multidragSteps.forEach((step) => {
            const stepPosition = { left: 0, top: 0 };
            const offset = stepStartOffsets.get(step.id) ?? [0, 0];
            stepPosition.left = position.x + offset[0];
            stepPosition.top = position.y + offset[1];
            stepStore.updateStep({ ...step, position: stepPosition });
        });

        multidragComments.forEach((comment) => {
            const offset = commentStartOffsets.get(comment.id) ?? [0, 0];
            const commentPosition = [position.x + offset[0], position.y + offset[1]] as [number, number];
            commentStore.changePosition(comment.id, commentPosition);
        });
    }

    return {
        multidragStart,
        multidragEnd,
        multidragMove,
    };
}
