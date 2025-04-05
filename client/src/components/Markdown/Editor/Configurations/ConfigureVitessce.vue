<template>
    <BAlert v-if="errorMessage" variant="warning" show>{{ errorMessage }}</BAlert>
    <div v-else class="p-2">
        <ConfigureHeader :has-changed="hasChanged" @ok="onOk" @cancel="$emit('cancel')" />
        <div v-if="contentObject.datasets && contentObject.datasets.length > 0">
            <div v-for="(dataset, datasetIndex) in contentObject.datasets" :key="datasetIndex">
                <Heading size="sm">{{ dataset.name }} ({{ dataset.uid || "n/a" }})</Heading>
                <div v-for="(file, fileIndex) in dataset.files" :key="fileIndex">
                    <ConfigureSelector
                        :labels="labels"
                        :object-name="getObjectName(file)"
                        :object-title="`${fileIndex + 1}: ${getFileName(file)}`"
                        object-type="history_dataset_id"
                        @change="onChange(file, $event)" />
                </div>
            </div>
        </div>
        <BAlert v-else variant="warning" show>No datasets found.</BAlert>
        <FormElementLabel title="Height" help="Specify the height of the view in pixel.">
            <FormNumber id="vitessce-height" v-model="height" :min="100" :max="1000" type="integer" @input="onHeight" />
        </FormElementLabel>
    </div>
</template>

<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import Vue, { computed, type Ref, ref, watch } from "vue";

import type { DatasetLabel, OptionType, WorkflowLabel } from "@/components/Markdown/Editor/types";
import { stringify } from "@/components/Markdown/Utilities/stringify";

import ConfigureHeader from "./ConfigureHeader.vue";
import ConfigureSelector from "./ConfigureSelector.vue";
import Heading from "@/components/Common/Heading.vue";
import FormNumber from "@/components/Form/Elements/FormNumber.vue";
import FormElementLabel from "@/components/Form/FormElementLabel.vue";

interface DatasetEntryType {
    files?: Array<FileEntryType>;
    name: string;
    uid: string;
}

interface FileEntryType {
    __gx_dataset_id?: string;
    __gx_dataset_label?: DatasetLabel;
    __gx_dataset_name?: string;
    fileType: string;
    url: string;
    options?: {
        obsIndex?: string;
        obsType?: string;
    };
}

interface VitessceType {
    datasets?: Array<DatasetEntryType>;
    __gx_height?: number;
    [key: string]: unknown;
}

const DEFAULT_HEIGHT = 400;

const props = defineProps<{
    name: string;
    content: string;
    labels?: Array<WorkflowLabel>;
}>();

const emit = defineEmits<{
    (e: "cancel"): void;
    (e: "change", content: string): void;
}>();

const contentObject: Ref<VitessceType> = ref({});
const errorMessage = ref();
const hasChanged = ref(false);
const height = ref();

const hasLabels = computed(() => props.labels !== undefined);

function getFileName(file: FileEntryType) {
    const fileDetailsParts = [file.options?.obsType, file.options?.obsIndex].filter(Boolean);
    const fileDetails = fileDetailsParts.length ? `(${fileDetailsParts.join(", ")})` : "";
    return `${file.fileType} ${fileDetails}`;
}

function getObjectName(file: FileEntryType) {
    return file.__gx_dataset_label?.input || file.__gx_dataset_label?.output || file.__gx_dataset_name || file.url;
}

function onChange(file: FileEntryType, option: OptionType) {
    if (hasLabels.value && option.label) {
        Vue.set(file, "url", undefined);
        Vue.set(file, "__gx_dataset_id", undefined);
        Vue.set(file, "__gx_dataset_name", undefined);
        Vue.set(file, "__gx_dataset_label", option.label);
    } else if (option.id) {
        Vue.set(file, "url", undefined);
        Vue.set(file, "__gx_dataset_id", option.id);
        Vue.set(file, "__gx_dataset_name", option.name);
        Vue.set(file, "__gx_dataset_label", undefined);
    }
    hasChanged.value = true;
}

function onHeight(newHeight: number) {
    contentObject.value.__gx_height = newHeight;
    hasChanged.value = true;
}

function onOk() {
    emit("change", stringify(contentObject.value));
}

function parseContent() {
    try {
        contentObject.value = JSON.parse(props.content);
        height.value = contentObject.value.__gx_height || DEFAULT_HEIGHT;
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
