<template>
    <BAlert v-if="errorMessage" variant="warning" show>{{ errorMessage }}</BAlert>
    <div v-else class="p-2">
        <ConfigureHeader :has-changed="hasChanged" @ok="onOk" @cancel="$emit('cancel')" />
        <ConfigureSelector
            :labels="labels"
            :object-name="objectName"
            object-type="history_dataset_id"
            @change="onChange" />
        <FormElementLabel title="Height" help="Specify the height of the view in pixel.">
            <FormNumber
                id="visualization-height"
                v-model="height"
                :min="100"
                :max="1000"
                type="integer"
                @input="onHeight" />
        </FormElementLabel>
    </div>
</template>

<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed, type Ref, ref, watch } from "vue";

import type { DatasetLabel, OptionType, WorkflowLabel } from "@/components/Markdown/Editor/types";
import { stringify } from "@/components/Markdown/Utilities/stringify";

import FormNumber from "@/components/Form/Elements/FormNumber.vue";
import FormElementLabel from "@/components/Form/FormElementLabel.vue";

import ConfigureHeader from "./ConfigureHeader.vue";
import ConfigureSelector from "./ConfigureSelector.vue";

interface contentType {
    dataset_id?: string;
    dataset_label?: DatasetLabel;
    dataset_name?: string;
    dataset_url?: string;
    height?: number;
    [key: string]: unknown;
}

const DEFAULT_HEIGHT = 400;

const props = defineProps<{
    content: string;
    labels?: Array<WorkflowLabel>;
}>();

const emit = defineEmits<{
    (e: "cancel"): void;
    (e: "change", content: string): void;
}>();

const contentObject: Ref<contentType> = ref({});
const errorMessage = ref("");
const hasChanged = ref(false);
const height = ref();

const hasLabels = computed(() => props.labels !== undefined);
const objectName = computed(() => contentObject.value.dataset_name || "...");

function onChange(option: OptionType) {
    if (contentObject.value) {
        if (hasLabels.value) {
            contentObject.value.dataset_label = option.label;
            contentObject.value.dataset_id = undefined;
            contentObject.value.dataset_url = undefined;
        } else {
            contentObject.value.dataset_id = option.id;
            contentObject.value.dataset_label = undefined;
            contentObject.value.dataset_url = undefined;
        }
        contentObject.value.dataset_name = option.name;
        hasChanged.value = true;
    }
}

function onHeight(newHeight: number) {
    contentObject.value.height = newHeight;
    hasChanged.value = true;
}

function onOk() {
    emit("change", stringify(contentObject.value));
}

function parseContent() {
    try {
        contentObject.value = JSON.parse(props.content);
        height.value = contentObject.value.height || DEFAULT_HEIGHT;
        errorMessage.value = "";
    } catch (e) {
        errorMessage.value = `Failed to parse: ${e}`;
    }
}

watch(
    () => props.content,
    () => parseContent(),
    { immediate: true }
);
</script>
