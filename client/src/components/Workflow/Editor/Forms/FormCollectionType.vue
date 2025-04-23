<script setup lang="ts">
import { ref, watch } from "vue";

import { isValidCollectionTypeStr } from "@/components/Workflow/Editor/modules/collectionTypeDescription";

import FormElement from "@/components/Form/FormElement.vue";

interface Props {
    value?: string;
}

const props = defineProps<Props>();

const currentValue = ref<string | undefined>(undefined);
const warning = ref<string | null>(null);
const error = ref<string | null>(null);

function onInput(newCollectionType: string | undefined) {
    emit("onChange", newCollectionType);
}

const collectionTypeOptions = [
    { value: "list", label: "List of Datasets" },
    { value: "paired", label: "Dataset Pair" },
    { value: "list:paired", label: "List of Dataset Pairs" },
];

function updateValue(newValue: string | undefined) {
    currentValue.value = newValue;
    warning.value = null;
    error.value = null;
    if (!newValue) {
        warning.value = "Typically, a value for this collection type should be specified.";
    } else if (!isValidCollectionTypeStr(newValue)) {
        error.value = "Invalid collection type";
    }
}

watch(() => props.value, updateValue, { immediate: true });
const emit = defineEmits(["onChange"]);
</script>

<template>
    <FormElement
        id="collection_type"
        :value="currentValue"
        :attributes="{ data: collectionTypeOptions, display: 'simple' }"
        :warning="warning ?? undefined"
        :error="error ?? undefined"
        title="Collection type"
        :optional="true"
        type="select"
        @input="onInput" />
</template>
