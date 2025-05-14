<script setup lang="ts">
import { BTable } from "bootstrap-vue";

import type {
    InvocationInput,
    InvocationInputParameter,
    InvocationOutput,
    InvocationOutputCollection,
} from "@/api/invocations";

import GenericHistoryItem from "@/components/History/Content/GenericItem.vue";

type InvocationStepTypes = InvocationInput | InvocationInputParameter | InvocationOutput | InvocationOutputCollection;

const props = defineProps<{
    parameters: InvocationStepTypes[];
    styledTable?: boolean;
}>();

function isData(value: unknown): value is InvocationInput | InvocationOutput | InvocationOutputCollection {
    return typeof value === "object" && value !== null && "src" in value;
}
function dataStepLabel(input: InvocationStepTypes): string {
    if ("label" in input && input.label) {
        return input.label;
    }
    if ("src" in input) {
        return input.src === "hda" ? "Input dataset" : "Input dataset collection";
    }
    return "Unnamed";
}
</script>

<template>
    <BTable
        small
        :outlined="props.styledTable"
        :striped="props.styledTable"
        :borderless="props.styledTable"
        :fields="['label', 'parameter_value']"
        :items="props.parameters">
        <template v-slot:cell(parameter_value)="{ item }">
            <GenericHistoryItem
                v-if="isData(item)"
                :item-id="item.id"
                :item-src="item.src"
                :data-label="dataStepLabel(item)" />
            <i v-else-if="item.parameter_value === null || item.parameter_value === undefined" class="text-muted">
                No value provided
            </i>
            <span v-else>
                {{ item.parameter_value }}
            </span>
        </template>
    </BTable>
</template>
