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
            class: 'Collection',
            elements: props.value.elements,
            identifier: props.value.name || 'Collection',
        }" />
    <FormDataUriElement
        v-else-if="isDataUriFile(props.value)"
        :value="{
            class: 'File',
            identifier: props.value.name || 'Dataset',
            location: props.value.location || props.value.url,
            ext: props.value.extension || props.value.filetype || props.value.ext,
        }" />
    <FormDataUriElement
        v-else-if="isDataUriData(props.value)"
        :value="{
            class: 'File',
            identifier: props.value.name || 'Data',
            location: props.value.location || props.value.url,
            ext: props.value.extension || props.value.filetype || props.value.ext,
        }" />
</template>
