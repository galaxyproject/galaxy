<template>
    <div class="p-2">
        <div class="d-flex justify-content-between align-items-start w-100">
            <div class="flex-grow-1 me-3">
                <Heading size="sm" separator>Attach Data</Heading>
                <div class="small mb-2">Fill in the fields below to map required inputs to this cell.</div>
            </div>
            <div class="d-flex gap-1">
                <CellButton title="Save" :icon="faSave" tooltip-placement="bottom" @click="onSave" />
                <CellButton title="Cancel" :icon="faTimes" tooltip-placement="bottom" @click="$emit('cancel')" />
            </div>
        </div>
        <div v-if="contentObject.datasets && contentObject.datasets.length > 0">
            <div v-for="(dataset, datasetIndex) in contentObject.datasets" :key="datasetIndex">
                <Heading size="sm">{{ dataset.name }} ({{ dataset.uid || "n/a" }})</Heading>
                <div v-for="(file, fileIndex) in dataset.files" :key="fileIndex">
                    <ConfigureSelector
                        :object-id="file.url"
                        :object-name="file.url"
                        :object-title="`${fileIndex + 1}: ${getFileName(file)}`"
                        object-type="history_dataset_id"
                        @change="onChange(file, $event)" />
                </div>
            </div>
        </div>
        <BAlert v-else variant="warning" show>No datasets found.</BAlert>
    </div>
</template>

<script setup lang="ts">
import { faSave, faTimes } from "@fortawesome/free-solid-svg-icons";
import { BAlert } from "bootstrap-vue";
import { type Ref, ref, watch } from "vue";

import type { OptionType, WorkflowLabel } from "@/components/Markdown/Editor/types";
import { stringify } from "@/components/Markdown/Utilities/stringify";
import { getAppRoot } from "@/onload";

import ConfigureSelector from "./ConfigureSelector.vue";
import Heading from "@/components/Common/Heading.vue";
import CellButton from "@/components/Markdown/Editor/CellButton.vue";

interface DatasetEntryType {
    files?: Array<FileEntryType>;
    name: string;
    uid: string;
}

interface FileEntryType {
    fileType: string;
    url: string;
    options?: {
        obsIndex?: string;
        obsType?: string;
    };
}

interface VitessceType {
    datasets?: Array<DatasetEntryType>;
}

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

function getFileName(file: FileEntryType) {
    const fileDetailsParts = [file.options?.obsType, file.options?.obsIndex].filter(Boolean);
    const fileDetails = fileDetailsParts.length ? `(${fileDetailsParts.join(", ")})` : "";
    return `${file.fileType} ${fileDetails}`;
}

function onChange(file: FileEntryType, option: OptionType) {
    if (option.id) {
        file.url = `${getAppRoot()}api/datasets/${option.id}/display`;
    }
}

function onSave() {
    emit("change", stringify(contentObject.value));
}

function parseContent() {
    try {
        contentObject.value = JSON.parse(props.content);
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
