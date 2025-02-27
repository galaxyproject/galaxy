import { toRefs } from "@vueuse/core";
import { computed, type Ref } from "vue";

import { type Step } from "@/stores/workflowStepStore";

export function useStepProps(step: Ref<Step>) {
    const {
        id: stepId,
        content_id: contentId,
        name,
        type,
        inputs: stepInputs,
        outputs: stepOutputs,
        post_job_actions: postJobActions,
        tool_state: toolState,
    } = toRefs(step);

    const label = computed(() => step.value.label ?? undefined);
    const annotation = computed(() => step.value.annotation ?? null);
    const configForm = computed(() => step.value.config_form);

    return {
        stepId,
        contentId,
        annotation,
        label,
        name,
        type,
        stepInputs,
        stepOutputs,
        configForm,
        postJobActions,
        toolState,
    };
}
