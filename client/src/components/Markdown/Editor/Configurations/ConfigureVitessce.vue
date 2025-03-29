<template>
    <div class="p-2">
        <div class="d-flex flex-row">
            <div class="w-100">
                <Heading size="sm" separator>Attach Data</Heading>
                <div class="small mb-2">Fill in the fields below to map required inputs to this cell.</div>
            </div>
            <CellButton class="align-self-start" title="Close" :icon="faTimes" @click="$emit('cancel')" />
        </div>
        <div v-if="true">
            <div v-for="(dataset, datasetIndex) in contentObject.datasets" :key="datasetIndex">
                <Heading size="sm">{{ dataset.name }} ({{ dataset.uid || "n/a" }})</Heading>
                <div v-for="(file, fileIndex) in dataset.files" :key="fileIndex">
                    <ConfigureSelector
                        object-id="232323"
                        :object-title="`${fileIndex + 1}: ${getFileName(file)}`"
                        object-type="history_dataset_id" />
                </div>
            </div>
        </div>
        <BAlert v-else variant="warning" show>No datasets found.</BAlert>
    </div>
</template>

<script setup lang="ts">
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { BAlert } from "bootstrap-vue";
import { type Ref, ref, watch } from "vue";

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
}>();

defineEmits<{
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
