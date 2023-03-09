import type { Step } from "@/stores/workflowStepStore";
import { toRefs } from "@vueuse/core";

import { computed, type Ref } from "vue";

export function useStepProps(step: Ref<Step>) {
    const {
        id: stepId,
        content_id: contentId,
        name,
        type,
        inputs: stepInputs,
        outputs: stepOutputs,
        config_form: configForm,
        post_job_actions: postJobActions,
    } = toRefs(step);

    const label = computed(() => step.value.label ?? undefined);
    const annotation = computed(() => step.value.annotation ?? null);

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
    };
}
