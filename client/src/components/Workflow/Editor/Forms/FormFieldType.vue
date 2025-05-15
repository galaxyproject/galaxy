<script setup lang="ts">
import { ref, watch } from "vue";

import { type FieldType } from "@/api";

import FormElement from "@/components/Form/FormElement.vue";

interface Props {
    value: FieldType;
    prefix: string;
}

const props = defineProps<Props>();

type SupportedFieldTypesAsString = "File" | "File?";

function fieldTypeToSupportedString(type: FieldType): SupportedFieldTypesAsString {
    if (Array.isArray(type) && type.length == 2) {
        return "File?";
    } else {
        return "File";
    }
}

const currentValue = ref<SupportedFieldTypesAsString>(fieldTypeToSupportedString(props.value));

function onInput(newType: SupportedFieldTypesAsString) {
    if (newType == "File?") {
        console.log("emitting File|null");
        emit("onChange", ["File", "null"]);
    } else {
        emit("onChange", "File");
    }
}

function updateValue(newValue: FieldType) {
    currentValue.value = fieldTypeToSupportedString(newValue);
}

const fieldTypes = [
    { value: "File", label: "File" },
    { value: "File?", label: "Optional File" },
];

watch(() => props.value, updateValue, { immediate: true });
const emit = defineEmits(["onChange"]);
</script>

<template>
    <div>
        <FormElement
            :id="prefix + '_type'"
            :value="currentValue"
            :attributes="{ data: fieldTypes }"
            title="Field type"
            :optional="false"
            type="select"
            @input="onInput" />
    </div>
</template>
