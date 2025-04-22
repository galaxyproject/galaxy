<script setup lang="ts">
import { BAlert, BTab } from "bootstrap-vue";
import { computed } from "vue";

import type { InvocationInput, WorkflowInvocationElementView } from "@/api/invocations";

import Heading from "../Common/Heading.vue";
import LoadingSpan from "../LoadingSpan.vue";
import ParameterStep from "./ParameterStep.vue";
import GenericHistoryItem from "components/History/Content/GenericItem.vue";

const OUTPUTS_NOT_AVAILABLE_YET_MSG =
    "Either no outputs have been produced yet, or no steps were checked to " +
    "mark their outputs as primary workflow outputs.";

const props = defineProps<{
    invocation: WorkflowInvocationElementView;
    terminal?: boolean;
}>();

const inputData = computed(() => Object.entries(props.invocation.inputs));

const outputs = computed(() => {
    const outputEntries = Object.entries(props.invocation.outputs);
    const outputCollectionEntries = Object.entries(props.invocation.output_collections);
    return [...outputEntries, ...outputCollectionEntries];
});

const parameters = computed(() => Object.values(props.invocation.input_step_parameters));

function dataInputStepLabel(key: string, input: InvocationInput) {
    const index: number = parseInt(key);
    const invocationStep = props.invocation.steps[index];
    let label = invocationStep && invocationStep.workflow_step_label;
    if (!label) {
        if (input.src === "hda") {
            label = "Input dataset";
        } else if (input.src === "hdca") {
            label = "Input dataset collection";
        }
    }
    return label;
}
</script>
<template>
    <span>
        <BTab title="Inputs">
            <div v-if="parameters.length">
                <Heading size="text" bold separator>Parameter Values</Heading>
                <div class="mx-1">
                    <ParameterStep :parameters="parameters" styled-table />
                </div>
            </div>
            <div v-if="inputData.length">
                <div
                    v-for="([key, input], index) in inputData"
                    :key="index"
                    :data-label="dataInputStepLabel(key, input)">
                    <Heading size="text" bold separator>
                        {{ dataInputStepLabel(key, input) }}
                    </Heading>
                    <GenericHistoryItem :item-id="input.id" :item-src="input.src" />
                </div>
            </div>
            <BAlert v-else show variant="info"> No input data was provided for this workflow invocation. </BAlert>
        </BTab>
        <BTab title="Outputs" :lazy="!props.terminal">
            <div v-if="outputs.length">
                <div v-for="([key, output], index) in outputs" :key="index">
                    <Heading size="text" bold separator>{{ key }}</Heading>
                    <GenericHistoryItem :item-id="output.id" :item-src="output.src" />
                </div>
            </div>
            <BAlert v-else show variant="info">
                <p>
                    <LoadingSpan v-if="!props.terminal" :message="OUTPUTS_NOT_AVAILABLE_YET_MSG" />
                    <span v-else v-localize>
                        No steps were checked to mark their outputs as primary workflow outputs.
                    </span>
                </p>
                <p>
                    To get outputs from a workflow in this tab, you need to check the
                    <i>
                        "Checked outputs will become primary workflow outputs and are available as subworkflow outputs."
                    </i>
                    option on individual outputs on individual steps in the workflow.
                </p>
            </BAlert>
        </BTab>
    </span>
</template>
