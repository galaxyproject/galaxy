import type { Step } from "@/stores/workflowStepStore";
import { toRefs } from "@vueuse/core";

import type { Ref } from "vue";

export function useStepProps(step: Ref<Step>) {
    const {
        id: stepId,
        content_id: contentId,
        annotation,
        label,
        name,
        type,
        inputs: stepInputs,
        outputs: stepOutputs,
        config_form: configForm,
        post_job_actions: postJobActions,
    } = toRefs(step);
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
