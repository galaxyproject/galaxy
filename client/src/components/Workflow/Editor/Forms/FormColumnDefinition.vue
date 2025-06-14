<script setup lang="ts">
import { BFormCheckbox } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import type { SampleSheetColumnDefinition, SampleSheetColumnDefinitionType } from "@/api";
import { columnTitleToTargetType } from "@/components/Collections/wizard/fetchWorkbooks";

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

const nameError = ref<string | undefined>(undefined);

function onName(name: string) {
    const state = stateCopy();
    state.name = name;
    const mappedToGalaxyColumn = columnTitleToTargetType(name);
    if (mappedToGalaxyColumn) {
        nameError.value =
            "This looks too much a column Galaxy uses automatically for all data imports, please choose a different name.";
    } else if (!/^[\w\-_ ?]*$/.test(name)) {
        nameError.value = "Column names can only contain alphanumeric characters, underscores, dashes, and spaces.";
    } else if (name.length < 1 || name.length > 100) {
        nameError.value = "Column names must be between 1 and 100 characters long.";
    } else {
        nameError.value = undefined;
    }
    emit("onChange", state, props.index);
}

function onDescription(description: string) {
    const state = stateCopy();
    state.description = description;
    emit("onChange", state, props.index);
}

function onType(newType: SampleSheetColumnDefinitionType) {
    const state = stateCopy();

    state.type = newType;
    state.default_value = _defaultByType(newType);
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

function asString(value: (string | number | boolean | null)[] | null | undefined): string {
    if (value) {
        return value.map((item) => (item ?? "").toString()).join(",");
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
        return parseInt(defaultIntAsStr.value);
    } else if (valueType == "float") {
        return parseFloat(defaultFloatAsStr.value);
    } else if (valueType == "boolean") {
        if (defaultBoolean.value === "null") {
            return null; // no default value
        } else if (defaultBoolean.value === "true") {
            return true;
        } else if (defaultBoolean.value === "false") {
            return false;
        }
    } else if (valueType == "element_identifier") {
        // doesn't make sense to let workflow author to set a default here.
        return null;
    } else {
        return null;
    }
}

function setIsOptional(isOptional: boolean) {
    const state = stateCopy();
    state.optional = isOptional;
    emit("onChange", state, props.index);
}

function setDefaultByType() {
    const state = stateCopy();
    state.default_value = _defaultByType();
    emit("onChange", state, props.index);
}

const booleanOptions = computed(() => {
    const options = [
        { value: "true", label: "True" },
        { value: "false", label: "False" },
    ];
    if (stateCopy().optional) {
        options.unshift({ value: "null", label: "No default value" });
    }
    return options;
});

const isOptional = ref(props.value.optional ?? false);
const defaultBoolean = ref(props.value.default_value === null ? "null" : props.value.default_value ? "true" : "false");
const defaultString = ref(props.value.default_value || "");
// form framework doesn't yield typed values it seems
const defaultIntAsStr = ref(props.value.default_value ? props.value.default_value.toString() : "0");
const defaultFloatAsStr = ref(props.value.default_value ? props.value.default_value.toString() : "0.0");

watch(isOptional, setIsOptional);
watch(defaultIntAsStr, setDefaultByType);
watch(defaultFloatAsStr, setDefaultByType);
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
            :error="nameError"
            help="Provide a short, unique name to describe this column."
            @input="onName" />
        <FormColumnDefinitionType :value="value.type" :prefix="prefix" @onChange="onType" />
        <FormElement
            :id="prefix + '_description'"
            :value="value.description"
            :attributes="{ area: true }"
            title="Description"
            type="text"
            help="Provide a longer description to help people running this workflow under what is expected to be entered in this column."
            @input="onDescription" />
        <FormElement
            v-if="value.type == 'string'"
            :id="prefix + '_enumerate_type'"
            :value="enumerateType"
            :attributes="{ data: enumerateTypes }"
            title="Restrict or Suggest Text Values?"
            :optional="false"
            type="select"
            @input="onEnumerateType" />
        <FormElement
            v-if="value.type == 'string' && enumerateType == 'staticRestrictions'"
            :id="prefix + '_restrictions'"
            :value="restrictionsAsString"
            title="Restricted Values"
            type="text"
            help="Comma-separated list of all permitted values"
            @input="onRestrictions" />
        <FormElement
            v-if="value.type == 'string' && enumerateType == 'staticSuggestions'"
            :id="prefix + '_suggestions'"
            :value="suggestionsAsString"
            title="Suggested Values"
            type="text"
            help="Comma-separated list of all suggested values"
            @input="onSuggestions" />
        <BFormCheckbox :id="prefix + '_optional'" v-model="isOptional"> Is this input optional? </BFormCheckbox>
        <div class="ui-form-title">
            <span class="ui-form-title-text"> Default Value </span>
        </div>
        <FormElement
            v-if="value.type == 'int'"
            :id="prefix + '_default_value'"
            v-model="defaultIntAsStr"
            type="integer" />
        <FormElement
            v-if="value.type == 'float'"
            :id="prefix + '_default_value'"
            v-model="defaultFloatAsStr"
            type="float" />
        <FormElement
            v-if="value.type == 'string'"
            :id="prefix + '_default_value'"
            v-model="defaultString"
            type="text" />
        <FormElement
            v-if="value.type == 'boolean'"
            :id="prefix + '_default_value'"
            v-model="defaultBoolean"
            :attributes="{ data: booleanOptions }"
            type="select" />

        <!--
        TODO: There are more fields to enter here including validations that vary based on the type chosen. There will
        be a lot of overlap with the same validation options for workflow parameters so it might be best to wait until
        those components can be developed in parallel.
        -->
    </div>
</template>

<style lang="scss" scoped>
@import "@/components/Form/_form-elements.scss";
</style>
