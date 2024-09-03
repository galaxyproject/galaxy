<script setup lang="ts">
import { BTab } from "bootstrap-vue";

import ParameterStep from "./ParameterStep.vue";
import GenericHistoryItem from "components/History/Content/GenericItem.vue";

const props = defineProps({
    invocation: {
        type: Object,
        required: true,
    },
});

interface HasSrc {
    src: string;
}

function dataInputStepLabel(key: number, input: HasSrc) {
    const invocationStep = props.invocation.steps[key];
    let label = invocationStep && invocationStep.workflow_step_label;
    if (!label) {
        if (input.src === "hda" || input.src === "ldda") {
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
        <BTab v-if="Object.keys(invocation.input_step_parameters).length" title="Parameters" lazy>
            <ParameterStep :parameters="Object.values(invocation.input_step_parameters)" />
        </BTab>
        <BTab v-if="Object.keys(invocation.inputs).length" title="Inputs" lazy>
            <div v-for="(input, key) in invocation.inputs" :key="input.id" :data-label="dataInputStepLabel(key, input)">
                <b>{{ dataInputStepLabel(key, input) }}</b>
                <GenericHistoryItem :item-id="input.id" :item-src="input.src" />
            </div>
        </BTab>
        <BTab v-if="Object.keys(invocation.outputs).length" title="Outputs" lazy>
            <div v-for="(output, key) in invocation.outputs" :key="output.id">
                <b>{{ key }}:</b>
                <GenericHistoryItem :item-id="output.id" :item-src="output.src" />
            </div>
        </BTab>
        <BTab v-if="Object.keys(invocation.output_collections).length" title="Output Collections" lazy>
            <div v-for="(output, key) in invocation.output_collections" :key="output.id">
                <b>{{ key }}:</b>
                <GenericHistoryItem :item-id="output.id" :item-src="output.src" />
            </div>
        </BTab>
    </span>
</template>
