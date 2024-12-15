<script setup lang="ts">
import { ref, watch } from "vue";

import { useTableSummary } from "@/components/Collections/tables";

import JaggedDataAlert from "./JaggedDataAlert.vue";

const emit = defineEmits(["onChange"]);

const isDragging = ref(false);
const { rawValue, jaggedDataWarning, table } = useTableSummary();

watch(table, (newValue: string[][]) => {
    emit("onChange", table.value);
});

const handleDrop = (event: DragEvent) => {
    isDragging.value = false;
    const file = event.dataTransfer?.files[0];
    if (file) {
        const reader = new FileReader();

        reader.onload = () => {
            rawValue.value = reader.result as string;
        };

        reader.onerror = () => {
            console.error("Failed to read file");
        };

        reader.readAsText(file); // Read the file as text
    }
};
</script>

<template>
    <div class="paste-data">
        <JaggedDataAlert :jaggedDataWarning="jaggedDataWarning" />
        <div
            class="dropzone"
            :class="{ highlight: isDragging }"
            @drop.prevent="handleDrop"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false">
            <textarea v-model="rawValue" class="p-2 mt-2" placeholder="Paste URIs and optional metadata here." />
        </div>
    </div>
</template>

<style scoped>
@import "theme/blue.scss";

.paste-data {
    min-width: 576px;
    display: flex;
    flex-flow: row wrap;
    margin-right: -15px;
    margin-left: -15px;
}

.paste-data textarea {
    resize: none;
    width: 100%;
    height: 300px;
    font-size: $font-size-base;
    -moz-border-radius: $border-radius-large;
    border-radius: $border-radius-large;
    border-color: $border-color;
    border-width: 2px;
}
.dropzone {
    padding: 7px !important;
    width: 100%;
}
.dropzone.highlight {
    border-width: 2px;
    border-color: $border-color;
    border-style: dashed;
    border-radius: $border-radius-large;
    -moz-border-radius: $border-radius-large;
}
</style>
