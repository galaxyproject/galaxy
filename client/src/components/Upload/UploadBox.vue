<script setup>
import { ref } from "vue";

const props = defineProps({
    multiple: Boolean,
});

const isDragging = ref(false);

const emit = defineEmits();

/** Handle files dropped into the upload box **/
function onDrop(evt) {
    isDragging.value = false;
    if (evt.dataTransfer) {
        emit("add", evt.dataTransfer.files);
    }
}
</script>

<template>
    <div
        class="upload-box"
        :class="{ highlight: isDragging }"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="onDrop">
        <slot />
    </div>
</template>

<style scoped>
.upload {
    height: 300px;
}
</style>
