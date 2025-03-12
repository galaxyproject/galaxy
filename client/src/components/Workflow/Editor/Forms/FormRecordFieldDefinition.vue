<script setup lang="ts">
import { type FieldDict, type FieldType } from "@/api";

import FormFieldType from "./FormFieldType.vue";
import FormElement from "@/components/Form/FormElement.vue";

interface Props {
    value: FieldDict;
    index: number;
    prefix: string; // prefix for ID objects
}

const props = defineProps<Props>();

const emit = defineEmits(["onChange"]);

function stateCopy(): FieldDict {
    return JSON.parse(JSON.stringify(props.value));
}

function onName(name: string) {
    const state = stateCopy();
    state.name = name;
    emit("onChange", state, props.index);
}

function onType(newType: FieldType) {
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
            help="Provide a short, unique name to describe this field."
            @input="onName" />
        <FormFieldType :prefix="prefix" :value="value.type" @onChange="onType" />
    </div>
</template>

<style lang="scss" scoped>
@import "@/components/Form/_form-elements.scss";
</style>
