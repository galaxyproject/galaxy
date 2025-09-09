<script setup lang="ts">
import { ref, watch } from "vue";

import type { SampleSheetColumnDefinitionType } from "@/api";

import FormElement from "@/components/Form/FormElement.vue";

interface Props {
    value: SampleSheetColumnDefinitionType;
    prefix: string;
}

const props = defineProps<Props>();

const currentValue = ref<SampleSheetColumnDefinitionType>(props.value);

function onInput(newType: SampleSheetColumnDefinitionType) {
    emit("onChange", newType);
}

function updateValue(newValue: SampleSheetColumnDefinitionType) {
    currentValue.value = newValue;
}

// workflow/modules.py uses:
// {"value": "text", "label": "Text"},
// {"value": "integer", "label": "Integer"},
// {"value": "float", "label": "Float"},
// {"value": "boolean", "label": "Boolean (True or False)"},
const columnTypes = [
    { value: "string", label: "Text" },
    { value: "int", label: "Integer" },
    { value: "float", label: "Float" },
    { value: "boolean", label: "Boolean (True or False)" },
    { value: "element_identifier", label: "Element Identifier" },
];

watch(() => props.value, updateValue, { immediate: true });
const emit = defineEmits(["onChange"]);
</script>

<template>
    <div>
        <FormElement
            :id="prefix + '_type'"
            :value="currentValue"
            :attributes="{ data: columnTypes }"
            title="Column type"
            :optional="false"
            type="select"
            @input="onInput" />
    </div>
</template>
