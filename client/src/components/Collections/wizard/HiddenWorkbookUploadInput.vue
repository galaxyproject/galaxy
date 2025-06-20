<script setup lang="ts">
import { ref } from "vue";

const emit = defineEmits(["onFileUpload"]);
const fileInputRef = ref<HTMLInputElement>();

function browse() {
    fileInputRef.value?.click();
}

function onFileUpload(event: Event) {
    emit("onFileUpload", event);
}

defineExpose({
    browse,
});
</script>

<template>
    <label style="display: none">
        <input ref="fileInputRef" type="file" accept=".xlsx" @change="onFileUpload" />
    </label>
</template>
