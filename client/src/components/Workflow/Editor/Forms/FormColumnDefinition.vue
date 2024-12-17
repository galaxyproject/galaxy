<script setup lang="ts">
import { type SampleSheetColumnDefinition, type SampleSheetColumnDefinitionType } from "@/api";

import FormColumnDefinitionType from "./FormColumnDefinitionType.vue";
import FormElement from "@/components/Form/FormElement.vue";

interface Props {
    value: SampleSheetColumnDefinition;
    index: number;
    prefix: string; // prefix for ID objects
}

const props = defineProps<Props>();

const emit = defineEmits(["onChange"]);

function stateCopy(): SampleSheetColumnDefinition {
    return JSON.parse(JSON.stringify(props.value));
}

function onName(name: string) {
    const state = stateCopy();
    state.name = name;
    emit("onChange", state, props.index);
}

function onType(newType: SampleSheetColumnDefinitionType) {
    const state = stateCopy();

    state.type = newType;
    emit("onChange", state, props.index);
}
</script>

<template>
    <div>
        <FormElement
            :id="prefix + '_name'"
            :value="value.name"
            title="Name"
            type="text"
            help="Provide a short, unique name to describe this column."
            @input="onName" />
        <FormColumnDefinitionType :value="value.type" :prefix="prefix" @onChange="onType" />
        <FormElement
            :id="prefix + '_description'"
            :value="value.description"
            title="Description"
            type="text"
            help="Provide a longer description to help people running this workflow under what is expected to be entered in this column."
            @input="onName" />
        TODO: There are more fields to enter here including restrictions and validations that vary based on the type
        chosen. There will be a lot of overlap with the same validation options for workflow parameters so it might be
        best to wait until those components can be developed in parallel.
    </div>
</template>
