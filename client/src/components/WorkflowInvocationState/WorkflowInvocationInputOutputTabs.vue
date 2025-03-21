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
            label = "输入数据集";
        } else if (input.src === "hdca") {
            label = "输入数据集集合";
        }
    }
    return label;
}
</script>
<template>
    <span v-if="invocation">
        <BTab v-if="Object.keys(invocation.input_step_parameters).length" title="参数" lazy>
            <ParameterStep :parameters="Object.values(invocation.input_step_parameters)" />
        </BTab>
        <BTab v-if="Object.keys(invocation.inputs).length" title="输入" lazy>
            <div v-for="(input, key) in invocation.inputs" :key="input.id" :data-label="dataInputStepLabel(key, input)">
                <b>{{ dataInputStepLabel(key, input) }}</b>
                <GenericHistoryItem :item-id="input.id" :item-src="input.src" />
            </div>
        </BTab>
        <BTab v-if="Object.keys(invocation.outputs).length" title="输出" lazy>
            <div v-for="(output, key) in invocation.outputs" :key="output.id">
                <b>{{ key }}:</b>
                <GenericHistoryItem :item-id="output.id" :item-src="output.src" />
            </div>
        </BTab>
        <BTab v-if="Object.keys(invocation.output_collections).length" title="输出集合" lazy>
            <div v-for="(output, key) in invocation.output_collections" :key="output.id">
                <b>{{ key }}:</b>
                <GenericHistoryItem :item-id="output.id" :item-src="output.src" />
            </div>
        </BTab>
    </span>
</template>
