import type { DatatypesMapperModel } from "@/components/Datatypes/model";
import { terminalFactory } from "@/components/Workflow/Editor/modules/terminals";
import type { Step, TerminalSource } from "@/stores/workflowStepStore";
import { ref, watch, type Ref } from "vue";

export function useTerminal(
    stepId: Ref<Step["id"]>,
    terminalSource: Ref<TerminalSource>,
    datatypesMapper: Ref<DatatypesMapperModel>
) {
    const terminal = ref();
    const isMappedOver = ref(false);
    watch(
        [stepId, terminalSource, datatypesMapper],
        () => {
            // rebuild terminal if any of the tracked dependencies change
            console.log("use Terminal terminal Factory");
            const newTerminal = terminalFactory(stepId.value, terminalSource.value, datatypesMapper.value);
            newTerminal.getInvalidConnectedTerminals();
            terminal.value = newTerminal;
            isMappedOver.value = newTerminal.isMappedOver();
        },
        {
            immediate: true,
        }
    );
    return { terminal: terminal as Ref<ReturnType<typeof terminalFactory>>, isMappedOver };
}
