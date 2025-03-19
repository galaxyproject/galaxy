<script setup lang="ts">
import { ref } from "vue";

import type { ZipContentFile } from "@/composables/zipExplorer";

interface Props {
    workflows: ZipContentFile[];
    files: ZipContentFile[];
    selectedItems: ZipContentFile[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "update:selectedItems", value: ZipContentFile[]): void;
}>();

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
        <h2>Contents</h2>

        <div v-if="props.workflows.length > 0">
            <strong>Workflows</strong>
            <ul>
                <li v-for="workflow in props.workflows" :key="workflow.path">
                    <input type="checkbox" :value="workflow" @change="toggleSelection(workflow)" />
                    {{ workflow.name }}
                </li>
            </ul>
        </div>

        <div v-if="props.files.length > 0">
            <strong>Files</strong>
            <ul>
                <li v-for="dataset in props.files" :key="dataset.path">
                    <input type="checkbox" :value="dataset" @change="toggleSelection(dataset)" />
                    {{ dataset.name }} <span class="text-muted">({{ dataset.type }})</span>
                </li>
            </ul>
        </div>
    </div>
</template>
