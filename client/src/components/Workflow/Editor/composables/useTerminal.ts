import type { DatatypesMapperModel } from "@/components/Datatypes/model";
import { terminalFactory } from "@/components/Workflow/Editor/modules/terminals";
import type { Step, TerminalSource } from "@/stores/workflowStepStore";
import { ref, watch, type Ref, computed } from "vue";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";

export function useTerminal(
    stepId: Ref<Step["id"]>,
    terminalSource: Ref<TerminalSource>,
    datatypesMapper: Ref<DatatypesMapperModel>
) {
    const terminal: Ref<ReturnType<typeof terminalFactory> | null> = ref(null);
    const stepStore = useWorkflowStepStore();
    const step = computed(() => stepStore.getStep(stepId.value));
    const isMappedOver = computed(() => stepStore.stepMapOver[stepId.value]?.isCollection ?? false);

    watch(
        [step, terminalSource, datatypesMapper],
        () => {
            // rebuild terminal if any of the tracked dependencies change
            const newTerminal = terminalFactory(stepId.value, terminalSource.value, datatypesMapper.value);
            newTerminal.getInvalidConnectedTerminals();
            terminal.value = newTerminal;
        },
        {
            immediate: true,
        }
    );
    return { terminal: terminal as Ref<ReturnType<typeof terminalFactory>>, isMappedOver };
}
