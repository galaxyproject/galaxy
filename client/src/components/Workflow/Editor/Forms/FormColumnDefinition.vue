<script setup lang="ts">
import { BFormCheckbox } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

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
    if (isOptional.value && newType != "string") {
        state.default_value = null;
    } else {
        state.default_value = _defaultByType(newType);
    }
    emit("onChange", state, props.index);
}

function onRestrictions(restrictionsAsText: string) {
    const state = stateCopy();
    state.suggestions = null;
    state.restrictions = parseCommaSeparatedValues(restrictionsAsText);
    emit("onChange", state, props.index);
}

function onSuggestions(restrictionsAsText: string) {
    const state = stateCopy();
    state.restrictions = null;
    state.suggestions = parseCommaSeparatedValues(restrictionsAsText);
    emit("onChange", state, props.index);
}

type EnumerateType = "staticRestrictions" | "staticSuggestions" | "none";

const initialEnumerateType = computed<EnumerateType>(() => {
    if (props.value.restrictions) {
        return "staticRestrictions";
    } else if (props.value.suggestions) {
        return "staticSuggestions";
    } else {
        return "none";
    }
});

const showOptional = computed(() => {
    return props.value.type !== "string";
});

const isOptional = computed(() => {
    return props.value.default_value == null;
});

// Modeled after language and values from workflow/modules.py for step parameters.
const enumerateTypes = [
    {
        value: "none",
        label: "Do not specify restrictions (default).",
    },
    {
        value: "staticRestrictions",
        label: "Provide list of all possible values.",
    },
    {
        value: "staticSuggestions",
        label: "Provide list of suggested values.",
    },
];
const enumerateType = ref<EnumerateType>(initialEnumerateType.value);

function onEnumerateType(newEnumerateType: EnumerateType) {
    enumerateType.value = newEnumerateType;
}

function parseCommaSeparatedValues(input: string): string[] {
    return input
        .split(",")
        .map((item) => item.trim())
        .filter((item) => item !== "");
}

function asString(value: (string | number | boolean)[] | null | undefined): string {
    if (value) {
        return value.map((item) => item.toString()).join(",");
    } else {
        return "";
    }
}

const restrictionsAsString = computed(() => {
    return asString(props.value.restrictions);
});

const suggestionsAsString = computed(() => {
    return asString(props.value.suggestions);
});

function _defaultByType(valueType_: string | undefined = undefined) {
    const valueType = valueType_ || props.value.type;
    if (valueType == "string") {
        return defaultString.value;
    } else if (valueType == "int") {
        return defaultInt.value;
    } else if (valueType == "float") {
        return defaultFloat.value;
    } else if (valueType == "boolean") {
        return defaultBoolean.value;
    } else {
        return "";
    }
}

function setIsOptional(isOptional: boolean) {
    console.log(isOptional);
    console.log("^ isOptional");
    const state = stateCopy();
    if (isOptional) {
        state.default_value = null;
    } else {
        state.default_value = _defaultByType();
    }
    emit("onChange", state, props.index);
}

function setDefaultByType() {
    const state = stateCopy();
    state.default_value = _defaultByType();
    emit("onChange", state, props.index);
}

const defaultInt = ref(0);
const defaultFloat = ref(0.0);
const defaultBoolean = ref(false);
const defaultString = ref("");

watch(defaultInt, setDefaultByType);
watch(defaultFloat, setDefaultByType);
watch(defaultBoolean, setDefaultByType);
watch(defaultString, setDefaultByType);
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
        <FormElement
            :id="prefix + '_enumerate_type'"
            :value="enumerateType"
            :attributes="{ data: enumerateTypes }"
            title="Restrict or Suggest Text Values?"
            :optional="false"
            type="select"
            @input="onEnumerateType" />
        <FormElement
            v-if="enumerateType == 'staticRestrictions'"
            :id="prefix + '_restrictions'"
            :value="restrictionsAsString"
            title="Restricted Values"
            type="text"
            help="Comma-separated list of all permitted values"
            @input="onRestrictions" />
        <FormElement
            v-if="enumerateType == 'staticSuggestions'"
            :id="prefix + '_suggestions'"
            :value="suggestionsAsString"
            title="Suggested Values"
            type="text"
            help="Comma-separated list of all suggested values"
            @input="onSuggestions" />
        <div class="ui-form-title">
            <span class="ui-form-title-text"> Default Value </span>
        </div>
        <BFormCheckbox v-if="showOptional" :id="prefix + '_optional'" :checked="isOptional" @input="setIsOptional">
            Is this input optional? If not you must specify a default value.
        </BFormCheckbox>
        <FormElement
            v-if="!isOptional && value.type == 'int'"
            :id="prefix + '_default_value_int'"
            v-model="defaultInt"
            type="integer" />
        <FormElement
            v-if="!isOptional && value.type == 'float'"
            :id="prefix + '_default_value_float'"
            v-model="defaultFloat"
            type="float" />
        <FormElement
            v-if="!isOptional && value.type == 'string'"
            :id="prefix + '_default_value_string'"
            v-model="defaultString"
            type="string" />

        TODO: There are more fields to enter here including validations that vary based on the type chosen. There will
        be a lot of overlap with the same validation options for workflow parameters so it might be best to wait until
        those components can be developed in parallel.
    </div>
</template>

<style lang="scss" scoped>
@import "@/components/Form/_form-elements.scss";
</style>
