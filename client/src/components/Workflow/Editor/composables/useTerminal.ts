import type { DatatypesMapperModel } from "@/components/Datatypes/model";
import { terminalFactory } from "@/components/Workflow/Editor/modules/terminals";
import type { Step, TerminalSource } from "@/stores/workflowStepStore";
import { ref, watchEffect, type Ref } from "vue";

export function useTerminal(
    stepId: Ref<Step["id"]>,
    terminalSource: Ref<TerminalSource>,
    datatypesMapper: Ref<DatatypesMapperModel>
): Ref<ReturnType<typeof terminalFactory>> {
    const terminal = ref();
    watchEffect(() => {
        const newTerminal = terminalFactory(stepId.value, terminalSource.value, datatypesMapper.value);
        console.log("built new terminal with datatypes mapper!", datatypesMapper.value);
        newTerminal.destroyInvalidConnections();
        terminal.value = newTerminal;
    });
    return terminal as Ref<ReturnType<typeof terminalFactory>>;
}
