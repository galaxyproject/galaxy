<script setup lang="ts">
import { computed, toRef } from "vue";

import { type SampleSheetColumnDefinitions } from "@/api";
import type { DatatypesMapperModel } from "@/components/Datatypes/model";
import type { Step } from "@/stores/workflowStepStore";

import { useToolState } from "../composables/useToolState";

import FormElement from "@/components/Form/FormElement.vue";
import FormCollectionType from "@/components/Workflow/Editor/Forms/FormCollectionType.vue";
import FormColumnDefinitions from "@/components/Workflow/Editor/Forms/FormColumnDefinitions.vue";
import FormDatatype from "@/components/Workflow/Editor/Forms/FormDatatype.vue";

interface ToolState {
    collection_type: string | null;
    optional: boolean;
    format: string | null;
    tag: string | null;
    column_definitions: SampleSheetColumnDefinitions;
}

const props = defineProps<{
    step: Step;
    datatypes: DatatypesMapperModel["datatypes"];
}>();

const stepRef = toRef(props, "step");
const { toolState } = useToolState(stepRef);

function cleanToolState(): ToolState {
    if (toolState.value) {
        return { ...toolState.value } as unknown as ToolState;
    } else {
        return {
            collection_type: null,
            optional: false,
            tag: null,
            format: null,
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

function onColumnDefinitions(newColumnDefinitions: SampleSheetColumnDefinitions) {
    const state = cleanToolState();
    console.log(newColumnDefinitions);
    state.column_definitions = newColumnDefinitions;
    emit("onChange", state);
}

const formatsAsList = computed(() => {
    const formatStr = toolState.value?.format as string | null;
    if (formatStr) {
        return formatStr.split(/\s*,\s*/);
    } else {
        return [];
    }
});

// parent is hacked to expect an initial change state, so replicate it I guess.
emit("onChange", cleanToolState());
</script>

<template>
    <div>
        <FormCollectionType :value="toolState?.collection_type" :optional="true" @onChange="onCollectionType" />
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
            v-if="toolState?.collection_type == 'sample_sheet'"
            :value="toolState?.column_definitions"
            @onChange="onColumnDefinitions" />
    </div>
</template>
