<script setup lang="ts">
import { type DataUri, isDataUriCollection, isDataUriData, isDataUriFile } from "./types";

import FormDataUriElement from "./FormDataUriElement.vue";

const props = defineProps<{
    value: DataUri;
}>();
</script>

<template>
    <FormDataUriElement
        v-if="isDataUriCollection(props.value)"
        :value="{
            ...props.value,
            identifier: props.value.name || 'Collection',
        }" />
    <FormDataUriElement
        v-else-if="isDataUriFile(props.value)"
        :value="{
            ...props.value,
            identifier: props.value.name || 'File',
        }" />
    <FormDataUriElement
        v-else-if="isDataUriData(props.value)"
        :value="{
            ...props.value,
            class: 'File',
            identifier: props.value.name || 'Data',
        }" />
</template>
