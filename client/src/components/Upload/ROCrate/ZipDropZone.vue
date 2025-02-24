<script setup lang="ts">
import { faArchive } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import { validateSingleZip } from "./rocrate.utils";

const emit = defineEmits<{
    (e: "dropError", errorMessage: string): void;
    (e: "dropSuccess", zipFile: File): void;
}>();

function onDrop(event: DragEvent) {
    event.preventDefault();

    const files = event.dataTransfer?.files;
    if (!files || files.length === 0) {
        console.log("No files dropped");
        return;
    }

    if (files.length !== 1) {
        emit("dropError", "Please drop a single RO-Crate Zip file");
        return;
    }

    const file = files[0];
    const errorMessage = validateSingleZip(file);
    if (errorMessage) {
        emit("dropError", errorMessage);
        return;
    }

    emit("dropSuccess", file!);
}

function reset(event: DragEvent) {
    event.preventDefault();
    emit("dropError", "");
}
</script>

<template>
    <div
        role="button"
        tabindex="0"
        class="drop-zone"
        @dragenter.prevent="reset"
        @dragover.prevent="reset"
        @dragleave.prevent="reset"
        @drop.prevent="onDrop">
        <div class="upload-helper">
            <FontAwesomeIcon class="mr-1" :icon="faArchive" />
            <span v-localize>Drop your RO-Crate Zip file here or paste URL below</span>
        </div>
    </div>
</template>
