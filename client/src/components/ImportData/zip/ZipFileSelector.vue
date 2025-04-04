<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { ref } from "vue";

import type { ImportableFile, ImportableZipContents } from "@/composables/zipExplorer";
import { useUserStore } from "@/stores/userStore";

import ZipFileEntryCard from "@/components/ImportData/zip/ZipFileEntryCard.vue";

interface Props {
    zipContents: ImportableZipContents;
    selectedItems: ImportableFile[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "update:selectedItems", value: ImportableFile[]): void;
}>();

const userStore = useUserStore();
const { isAnonymous } = storeToRefs(userStore);

const localSelectedItems = ref<ImportableFile[]>(props.selectedItems);

function toggleSelection(item: ImportableFile) {
    const index = localSelectedItems.value.findIndex((selected) => selected.path === item.path);
    if (index === -1) {
        localSelectedItems.value.push(item);
    } else {
        localSelectedItems.value.splice(index, 1);
    }
    emit("update:selectedItems", localSelectedItems.value);
}
</script>

<template>
    <div class="zip-file-selector">
        <div v-if="props.zipContents.workflows.length > 0">
            <h3>Workflows</h3>
            <BAlert v-if="isAnonymous" variant="warning" show fade>You must be logged in to import workflows</BAlert>
            <p>Here you can select workflows compatible with Galaxy and import them into your account.</p>
            <div v-for="workflow in props.zipContents.workflows" :key="workflow.path" class="d-flex flex-column">
                <label v-b-tooltip.hover title="Select this workflow to import">
                    <input
                        type="checkbox"
                        :value="workflow"
                        :disabled="isAnonymous"
                        :checked="localSelectedItems.includes(workflow)"
                        @change="toggleSelection(workflow)" />
                    <ZipFileEntryCard :file="workflow" />
                </label>
            </div>
        </div>

        <div v-if="props.zipContents.files.length > 0">
            <h3>Files</h3>
            <p>Here you can select individual files to import into your <b>current history</b>.</p>
            <div v-for="dataset in props.zipContents.files" :key="dataset.path" class="d-flex flex-column">
                <label v-b-tooltip.hover title="Select this file to import">
                    <input
                        type="checkbox"
                        :value="dataset"
                        :checked="localSelectedItems.includes(dataset)"
                        @change="toggleSelection(dataset)" />
                    <ZipFileEntryCard :file="dataset" />
                </label>
            </div>
        </div>
    </div>
</template>
