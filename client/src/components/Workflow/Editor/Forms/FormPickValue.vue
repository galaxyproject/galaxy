<script setup lang="ts">
import { toRef, watch } from "vue";

import type { DatatypesMapperModel } from "@/components/Datatypes/model";
import type { InputTerminalSource, PostJobActions, Step } from "@/stores/workflowStepStore";

import { useToolState } from "../composables/useToolState";

import Heading from "@/components/Common/Heading.vue";
import FormElement from "@/components/Form/FormElement.vue";
import FormSection from "@/components/Workflow/Editor/Forms/FormSection.vue";

interface ToolState {
    mode: string;
    num_inputs: number;
}

const props = withDefaults(
    defineProps<{
        step: Step;
        datatypes?: DatatypesMapperModel["datatypes"];
        nodeInputs?: InputTerminalSource[];
        postJobActions?: PostJobActions;
    }>(),
    {
        datatypes: undefined,
        nodeInputs: () => [],
        postJobActions: () => ({}),
    },
);

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

const emit = defineEmits(["onChange", "onChangePostJobActions"]);

const modeOptions = [
    ["First non-null (error if all null)", "first_non_null"],
    ["First non-null (skip if all null)", "first_or_skip"],
    ["The only non-null (error if != 1)", "the_only_non_null"],
    ["All non-null (as collection)", "all_non_null"],
];

function onMode(newMode: string) {
    const state = cleanToolState();
    state.mode = newMode;
    emit("onChange", state);
}

function onChangePostJobActions(postJobActions: PostJobActions) {
    emit("onChangePostJobActions", postJobActions);
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
    { deep: true },
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
        <div v-if="datatypes && step.outputs && step.outputs.length > 0" class="mt-2 mb-4">
            <Heading h2 separator bold size="sm"> Additional Options </Heading>
            <FormSection
                :id="step.id"
                :node-inputs="nodeInputs ?? []"
                :node-outputs="step.outputs"
                :step="step"
                :datatypes="datatypes"
                :post-job-actions="postJobActions ?? {}"
                @onChange="onChangePostJobActions" />
        </div>
    </div>
</template>
