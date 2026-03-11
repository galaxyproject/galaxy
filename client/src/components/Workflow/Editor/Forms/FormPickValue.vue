<script setup lang="ts">
import { toRef, watch } from "vue";

import type { Step } from "@/stores/workflowStepStore";

import { useToolState } from "../composables/useToolState";

import FormElement from "@/components/Form/FormElement.vue";

interface ToolState {
    mode: string;
    num_inputs: number;
}

const props = defineProps<{
    step: Step;
}>();

const stepRef = toRef(props, "step");
const { toolState } = useToolState(stepRef);

function asToolState(ts: unknown): ToolState {
    const raw = ts as Record<string, unknown>;
    return {
        mode: (raw.mode as string) ?? "first_non_null",
        num_inputs: (raw.num_inputs as number) ?? 2,
    };
}

function cleanToolState(): ToolState {
    if (toolState.value) {
        return asToolState({ ...toolState.value });
    }
    return { mode: "first_non_null", num_inputs: 2 };
}

const emit = defineEmits(["onChange"]);

const modeOptions = [
    { value: "first_non_null", label: "First non-null (error if all null)" },
    { value: "first_or_skip", label: "First non-null (skip if all null)" },
    { value: "the_only_non_null", label: "The only non-null (error if != 1)" },
    { value: "all_non_null", label: "All non-null (as collection)" },
];

function onMode(newMode: string) {
    const state = cleanToolState();
    state.mode = newMode;
    emit("onChange", state);
}

// Grow-on-connect: watch step connections, add terminal when last empty one gets connected
watch(
    () => props.step.input_connections,
    (connections) => {
        const state = cleanToolState();
        const lastTerminalName = `input_${state.num_inputs}`;
        if (connections && connections[lastTerminalName]) {
            state.num_inputs = state.num_inputs + 1;
            emit("onChange", state);
        }
    },
    { deep: true }
);

// Dummy initial emit (same pattern as FormInputCollection — resets initialChange guard)
emit("onChange", cleanToolState());
</script>

<template>
    <div>
        <FormElement
            id="mode"
            :value="asToolState(toolState).mode"
            title="Selection Mode"
            type="select"
            :options="modeOptions"
            help="How to select among the connected inputs."
            @input="onMode" />
    </div>
</template>
