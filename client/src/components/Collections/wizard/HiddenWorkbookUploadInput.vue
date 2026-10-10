<script setup lang="ts">
import { ref } from "vue";

defineProps<{
    // Lets tests tell the wizard header's input apart from the one in the upload card.
    dataDescription: string;
}>();

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
        <input
            ref="fileInputRef"
            :data-description="dataDescription"
            type="file"
            accept=".xlsx,.xls,.tsv,.csv,.tabular"
            @change="onFileUpload" />
    </label>
</template>
