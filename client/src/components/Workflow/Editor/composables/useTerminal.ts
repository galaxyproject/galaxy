import type { DatatypesMapperModel } from "@/components/Datatypes/model";
import { terminalFactory } from "@/components/Workflow/Editor/modules/terminals";
import type { Step, TerminalSource } from "@/stores/workflowStepStore";
import { ref, watchEffect, type Ref } from "vue";

export function useTerminal(
    stepId: Ref<Step["id"]>,
    terminalSource: Ref<TerminalSource>,
    datatypesMapper: Ref<DatatypesMapperModel>
) {
    const terminal = ref();
    const isMappedOver = ref(false);
    watchEffect(() => {
        // rebuild terminal if any of the tracked dependencies change
        const newTerminal = terminalFactory(stepId.value, terminalSource.value, datatypesMapper.value);
        newTerminal.getInvalidConnectedTerminals();
        terminal.value = newTerminal;
        isMappedOver.value = newTerminal.isMappedOver();
    });
    return { terminal: terminal as Ref<ReturnType<typeof terminalFactory>>, isMappedOver };
}
