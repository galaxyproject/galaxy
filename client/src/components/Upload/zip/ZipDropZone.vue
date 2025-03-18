<script setup lang="ts">
import { faArchive } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";

import { isZipFile } from "./utils";

const isDragging = ref(false);

const emit = defineEmits<{
    (e: "dropError", errorMessage: string): void;
    (e: "dropSuccess", zipFile: File): void;
}>();

function onDrop(event: DragEvent) {
    isDragging.value = false;

    const files = event.dataTransfer?.files;
    if (!files || files.length === 0) {
        return;
    }

    if (files.length !== 1) {
        emit("dropError", "Please drop a single Zip file");
        return;
    }

    const file = files[0];
    const errorMessage = isZipFile(file);
    if (errorMessage) {
        emit("dropError", errorMessage);
        return;
    }

    emit("dropSuccess", file!);
}

function onDragEnter(event: DragEvent) {
    event.preventDefault();
    isDragging.value = true;
    resetError();
}

function onDragLeave(event: DragEvent) {
    event.preventDefault();
    isDragging.value = false;
}

function onDragOver(event: DragEvent) {
    event.preventDefault();
    isDragging.value = true;
}

function resetError() {
    emit("dropError", "");
}
</script>

<template>
    <div
        role="button"
        tabindex="0"
        class="drop-zone h-100"
        @dragenter.prevent="onDragEnter"
        @dragover.prevent="onDragOver"
        @dragleave.prevent="onDragLeave"
        @drop.prevent="onDrop">
        <div class="helper" :class="{ highlight: isDragging }">
            <FontAwesomeIcon class="mr-1" :icon="faArchive" />
            <span v-localize>Drop your ZIP archive here, choose a local file or paste a URL below</span>
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";

.helper {
    pointer-events: none;

    font-size: x-large;
    color: $border-color;

    display: flex;
    justify-content: center;
    align-items: center;
    height: 100%;
}

.highlight {
    color: $brand-info;
    opacity: 0.8;
}
</style>
