<script setup lang="ts">
import { computed, ref, toRef } from "vue";

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
    format: string | string[] | null;
    tag: string | null;
    fields: FieldDict[] | null;
    column_definitions: SampleSheetColumnDefinitions;
}

const props = defineProps<{
    step: Step;
    datatypes: DatatypesMapperModel["datatypes"];
}>();

const stepRef = toRef(props, "step");
const { toolState: stepToolState } = useToolState(stepRef);

const DEFAULT_TOOL_STATE: Readonly<ToolState> = Object.freeze({
    collection_type: null,
    optional: false,
    tag: null,
    format: null,
    fields: null,
    column_definitions: null,
});

/**
 * The form owns its values, like `FormDisplay` does for tool steps. Edits are
 * sent to the server as a full snapshot and only reach the step store once the
 * server has echoed them back, so reading the store on every edit would resend
 * the previous value of a field whose request is still pending. The state is
 * seeded from the step when the component mounts; `FormDefault` re-keys the
 * component on undo and redo so it is seeded again from the restored step.
 */
const toolState = ref<ToolState>({
    ...DEFAULT_TOOL_STATE,
    ...(stepToolState.value as Partial<ToolState>),
});

function cleanToolState(): ToolState {
    return { ...toolState.value };
}

const emit = defineEmits(["onChange"]);

function emitChange(edit: Partial<ToolState>) {
    toolState.value = { ...toolState.value, ...edit };
    emit("onChange", cleanToolState());
}

function onDatatype(newDatatype: string[]) {
    emitChange({ format: newDatatype.join(",") });
}

function onTags(newTags: string | null) {
    emitChange({ tag: newTags });
}

function onOptional(newOptional: boolean) {
    emitChange({ optional: newOptional });
}

function onCollectionType(newCollectionType: string | null) {
    emitChange({ collection_type: newCollectionType });
}

function onRecordFieldDefinitions(newRecordFieldDefinitions: FieldDict[]) {
    emitChange({ fields: newRecordFieldDefinitions });
}

const isRecordType = computed(() => {
    const collectionType = toolState.value.collection_type;
    return collectionType == "record" || collectionType == "list:record" || collectionType == "sample_sheet:record";
});

/** Debounce timer to prevent constant object creation while typing */
let columnDefinitionsTimer: ReturnType<typeof setTimeout> | null = null;

function onColumnDefinitions(newColumnDefinitions: SampleSheetColumnDefinitions) {
    // If existing timer, clear it to prevent emitting the value while the user is still typing
    if (columnDefinitionsTimer) {
        clearTimeout(columnDefinitionsTimer);
    }

    columnDefinitionsTimer = setTimeout(() => {
        emitChange({ column_definitions: newColumnDefinitions });
        columnDefinitionsTimer = null;
    }, 500);
}

const formatsAsList = computed(() => {
    const formatStr = toolState.value.format;
    if (formatStr && typeof formatStr === "string") {
        return formatStr.split(/\s*,\s*/);
    } else if (formatStr) {
        return formatStr;
    } else {
        return [];
    }
});

const collectionType = computed(() => {
    return toolState.value.collection_type ?? undefined;
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
        <FormElement id="optional" :value="toolState.optional" title="Optional" type="boolean" @input="onOptional" />
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
            :value="toolState.tag"
            title="Tag filter"
            :optional="true"
            type="text"
            help="Tags to automatically filter inputs"
            @input="onTags" />
        <FormColumnDefinitions
            v-if="isSampleSheetType"
            :collection-type="sampleSheetCollectionType"
            :value="toolState.column_definitions"
            @onChange="onColumnDefinitions" />
        <FormRecordFieldDefinitions
            v-if="isRecordType"
            :value="toolState.fields || []"
            @onChange="onRecordFieldDefinitions" />
    </div>
</template>
