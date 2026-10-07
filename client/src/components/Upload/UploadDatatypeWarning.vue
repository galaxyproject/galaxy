<script setup lang="ts">
import { faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

defineProps<{
    message?: string | null;
}>();
</script>

<template>
    <span v-if="message" class="upload-datatype-warning d-block small mt-1">
        <FontAwesomeIcon :icon="faExclamationTriangle" class="text-warning mr-1" />
        {{ message }}
    </span>
</template>

<style scoped>
.upload-datatype-warning {
    white-space: normal;
    word-break: normal;
    overflow-wrap: anywhere;
    font-weight: normal;
    line-height: 1.4;
}
</style>
