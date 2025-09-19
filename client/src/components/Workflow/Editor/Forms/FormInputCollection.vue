<script setup lang="ts">
import { computed, toRef } from "vue";

import type { FieldDict, SampleSheetColumnDefinitions } from "@/api";
import type { SampleSheetCollectionType } from "@/api/datasetCollections";
import type { DatatypesMapperModel } from "@/components/Datatypes/model";
import type { Step } from "@/stores/workflowStepStore";

import { useToolState } from "../composables/useToolState";

import FormElement from "@/components/Form/FormElement.vue";
import FormCollectionType from "@/components/Workflow/Editor/Forms/FormCollectionType.vue";
import FormColumnDefinitions from "@/components/Workflow/Editor/Forms/FormColumnDefinitions.vue";
import FormDatatype from "@/components/Workflow/Editor/Forms/FormDatatype.vue";
import FormRecordFieldDefinitions from "@/components/Workflow/Editor/Forms/FormRecordFieldDefinitions.vue";

interface ToolState {
    collection_type: string | null;
    optional: boolean;
    format: string | null;
    tag: string | null;
    fields: FieldDict[] | null;
    column_definitions: SampleSheetColumnDefinitions;
}

const props = defineProps<{
    step: Step;
    datatypes: DatatypesMapperModel["datatypes"];
}>();

function asToolState(toolState: unknown) {
    return toolState as ToolState;
}

const stepRef = toRef(props, "step");
const { toolState } = useToolState(stepRef);

function cleanToolState(): ToolState {
    if (toolState.value) {
        return asToolState({ ...toolState.value });
    } else {
        return {
            collection_type: null,
            optional: false,
            tag: null,
            format: null,
            fields: null,
            column_definitions: null,
        };
    }
}

const emit = defineEmits(["onChange"]);

function onDatatype(newDatatype: string[]) {
    const state = cleanToolState();
    state.format = newDatatype.join(",");
    emit("onChange", state);
}

function onTags(newTags: string | null) {
    const state = cleanToolState();
    state.tag = newTags;
    emit("onChange", state);
}

function onOptional(newOptional: boolean) {
    const state = cleanToolState();
    state.optional = newOptional;
    emit("onChange", state);
}

function onCollectionType(newCollectionType: string | null) {
    const state = cleanToolState();
    state.collection_type = newCollectionType;
    emit("onChange", state);
}

function onRecordFieldDefinitions(newRecordFieldDefinitions: FieldDict[]) {
    const state = cleanToolState();
    state.fields = newRecordFieldDefinitions;
    emit("onChange", state);
}

const isRecordType = computed(() => {
    const collectionType = asToolState(toolState.value).collection_type;
    return collectionType == "record" || collectionType == "list:record" || collectionType == "sample_sheet:record";
});

function onColumnDefinitions(newColumnDefinitions: SampleSheetColumnDefinitions) {
    const state = cleanToolState();
    console.log(newColumnDefinitions);
    state.column_definitions = newColumnDefinitions;
    emit("onChange", state);
}

const formatsAsList = computed(() => {
    const formatStr = toolState.value?.format as string | string[] | null;
    if (formatStr && typeof formatStr === "string") {
        return formatStr.split(/\s*,\s*/);
    } else if (formatStr) {
        return formatStr;
    } else {
        return [];
    }
});

const collectionType = computed(() => {
    return toolState.value.collection_type as string | undefined;
});

const isSampleSheetType = computed(() => {
    return collectionType.value?.startsWith("sample_sheet");
});

const sampleSheetCollectionType = computed(() => {
    return toolState.value.collection_type as SampleSheetCollectionType;
});

// Terrible Hack: The parent component (./FormDefault.vue) ignores the first update, so
// I am sending a dummy update here. Ideally, the parent FormDefault would not expect this.
emit("onChange", cleanToolState());
</script>

<template>
    <div>
        <FormCollectionType :value="collectionType" :optional="true" @onChange="onCollectionType" />
        <FormElement id="optional" :value="toolState?.optional" title="Optional" type="boolean" @input="onOptional" />
        <FormDatatype
            id="format"
            :value="formatsAsList"
            :datatypes="datatypes"
            title="Format(s)"
            :multiple="true"
            help="Leave empty to auto-generate filtered list at runtime based on connections."
            @onChange="onDatatype" />
        <FormElement
            id="tag"
            :value="toolState?.tag"
            title="Tag filter"
            :optional="true"
            type="text"
            help="Tags to automatically filter inputs"
            @input="onTags" />
        <FormColumnDefinitions
            v-if="isSampleSheetType"
            :collection-type="sampleSheetCollectionType"
            :value="asToolState(toolState).column_definitions"
            @onChange="onColumnDefinitions" />
        <FormRecordFieldDefinitions
            v-if="isRecordType"
            :value="asToolState(toolState).fields || []"
            @onChange="onRecordFieldDefinitions" />
    </div>
</template>
