<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { ref } from "vue";

import type { ImportableZipContents, ZipContentFile } from "@/composables/zipExplorer";
import { useUserStore } from "@/stores/userStore";

interface Props {
    zipContents: ImportableZipContents;
    selectedItems: ZipContentFile[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "update:selectedItems", value: ZipContentFile[]): void;
}>();

const userStore = useUserStore();
const { isAnonymous } = storeToRefs(userStore);

const localSelectedItems = ref<ZipContentFile[]>(props.selectedItems);

function toggleSelection(item: ZipContentFile) {
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
            <ul>
                <li v-for="workflow in props.zipContents.workflows" :key="workflow.path">
                    <label v-b-tooltip.hover title="Select this workflow to import">
                        <input
                            type="checkbox"
                            :value="workflow"
                            :disabled="isAnonymous"
                            :checked="localSelectedItems.includes(workflow)"
                            @change="toggleSelection(workflow)" />
                        {{ workflow.name }}
                    </label>
                </li>
            </ul>
        </div>

        <div v-if="props.zipContents.files.length > 0">
            <h3>Files</h3>
            <p>Here you can select individual files to import into your <b>current history</b>.</p>
            <ul>
                <li v-for="dataset in props.zipContents.files" :key="dataset.path">
                    <label v-b-tooltip.hover title="Select this file to import">
                        <input
                            type="checkbox"
                            :value="dataset"
                            :checked="localSelectedItems.includes(dataset)"
                            @change="toggleSelection(dataset)" />
                        {{ dataset.name }}
                    </label>
                </li>
            </ul>
        </div>
    </div>
</template>
