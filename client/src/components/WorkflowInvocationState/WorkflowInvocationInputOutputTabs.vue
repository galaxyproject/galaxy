<script setup lang="ts">
import { BTab } from "bootstrap-vue";
import { computed } from "vue";

import type { InvocationInput, WorkflowInvocationElementView } from "@/api/invocations";

import Heading from "../Common/Heading.vue";
import ParameterStep from "./ParameterStep.vue";
import GenericHistoryItem from "components/History/Content/GenericItem.vue";

const props = defineProps<{
    invocation: WorkflowInvocationElementView;
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
    <span v-if="invocation">
        <BTab v-if="inputData.length || parameters.length" title="Inputs" lazy>
            <div v-if="parameters.length">
                <Heading size="text" bold separator>Parameter Values</Heading>
                <div class="mx-1">
                    <ParameterStep :parameters="parameters" />
                </div>
            </div>
            <div v-for="([key, input], index) in inputData" :key="index" :data-label="dataInputStepLabel(key, input)">
                <Heading size="text" bold separator>
                    {{ dataInputStepLabel(key, input) }}
                </Heading>
                <GenericHistoryItem :item-id="input.id" :item-src="input.src" />
            </div>
        </BTab>
        <BTab v-if="outputs.length" title="Outputs" lazy>
            <div v-for="([key, output], index) in outputs" :key="index">
                <Heading size="text" bold separator>{{ key }}</Heading>
                <GenericHistoryItem :item-id="output.id" :item-src="output.src" />
            </div>
        </BTab>
    </span>
</template>
