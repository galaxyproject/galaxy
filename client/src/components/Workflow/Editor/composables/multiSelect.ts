import { computed } from "vue";

import { useWorkflowStores } from "@/composables/workflowStores";
import type { Step } from "@/stores/workflowStepStore";
import { ensureDefined } from "@/utils/assertions";

export function useMultiSelect() {
    const { commentStore, stateStore, stepStore } = useWorkflowStores();

    function deselectAll() {
        commentStore.clearMultiSelectedComments();
        stateStore.clearStepMultiSelection();
    }

    const selectedCommentsCount = computed(() => commentStore.multiSelectedCommentIds.length);
    const selectedStepsCount = computed(() => stateStore.multiSelectedStepIds.length);
    const anySelected = computed(() => selectedCommentsCount.value > 0 || selectedStepsCount.value > 0);

    const multiSelectedComments = computed(() =>
        commentStore.multiSelectedCommentIds.map((id) => ensureDefined(commentStore.commentsRecord[id]))
    );

    type StepWithPosition = Step & { position: NonNullable<Step["position"]> };

    const multiSelectedSteps = computed<StepWithPosition[]>(() =>
        stateStore.multiSelectedStepIds.flatMap((id) => {
            const step = ensureDefined(stepStore.steps[id]);

            if (step.position) {
                return [step] as StepWithPosition[];
            } else {
                return [];
            }
        })
    );

    return {
        selectedCommentsCount,
        selectedStepsCount,
        anySelected,
        deselectAll,
        multiSelectedComments,
        multiSelectedSteps,
    };
}
