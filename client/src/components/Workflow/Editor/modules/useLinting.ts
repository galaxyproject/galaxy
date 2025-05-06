import type { Ref } from "vue";
import { ref, watch } from "vue";

import type { DatatypesMapperModel } from "@/components/Datatypes/model";
import { useWorkflowStores } from "@/composables/workflowStores";
import type { Steps } from "@/stores/workflowStepStore";

import type { LintState } from "./linting";
import { getDisconnectedInputs, getMissingMetadata, getUnlabeledOutputs, getUntypedParameters } from "./linting";
import { getUntypedWorkflowParameters, type UntypedParameters } from "./parameters";

export function useLintData(workflowId: Ref<string>, steps: Ref<Steps>, datatypesMapper: Ref<DatatypesMapperModel>) {
    const workflowStores = useWorkflowStores(workflowId);

    const untypedParameters = ref<UntypedParameters>();
    const untypedParameterWarnings = ref<LintState[]>([]);
    const disconnectedInputs = ref<LintState[]>([]);
    const unlabeledOutputs = ref<LintState[]>([]);
    const missingMetadata = ref<LintState[]>([]);

    watch(
        () => [steps],
        () => {
            if (datatypesMapper.value) {
                untypedParameters.value = getUntypedWorkflowParameters(steps.value);
                untypedParameterWarnings.value = getUntypedParameters(untypedParameters.value);
                disconnectedInputs.value = getDisconnectedInputs(steps.value, datatypesMapper.value, workflowStores);
                unlabeledOutputs.value = getUnlabeledOutputs(steps.value);
                missingMetadata.value = getMissingMetadata(steps.value);
            }
        },
        { immediate: true, deep: true }
    );

    return { untypedParameters, untypedParameterWarnings, disconnectedInputs, unlabeledOutputs, missingMetadata };
}
