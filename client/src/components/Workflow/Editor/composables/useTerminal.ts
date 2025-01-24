import { computed, type Ref, ref, watch } from "vue";

import { type DatatypesMapperModel } from "@/components/Datatypes/model";
import { terminalFactory } from "@/components/Workflow/Editor/modules/terminals";
import { useWorkflowStores } from "@/composables/workflowStores";
import { type Step, type TerminalSource } from "@/stores/workflowStepStore";

export function useTerminal(
    stepId: Ref<Step["id"]>,
    terminalSource: Ref<TerminalSource>,
    datatypesMapper: Ref<DatatypesMapperModel>
) {
    const terminal: Ref<ReturnType<typeof terminalFactory> | null> = ref(null);
    const stores = useWorkflowStores();
    const step = computed(() => stores.stepStore.getStep(stepId.value));
    const isMappedOver = computed(() => stores.stepStore.stepMapOver[stepId.value]?.isCollection ?? false);

    watch(
        [step, terminalSource, datatypesMapper],
        () => {
            // rebuild terminal if any of the tracked dependencies change
            const newTerminal = terminalFactory(stepId.value, terminalSource.value, datatypesMapper.value, stores);
            newTerminal.getInvalidConnectedTerminals();
            terminal.value = newTerminal;
        },
        {
            immediate: true,
        }
    );
    return { terminal: terminal as Ref<ReturnType<typeof terminalFactory>>, isMappedOver };
}
