<script setup lang="ts">
import type { ExampleData } from "./types";

import FormExampleDataElement from "./FormExampleDataElement.vue";

const props = defineProps<{
    value: ExampleData;
}>();
</script>

<template>
    <FormExampleDataElement
        v-if="props.value.class === 'Collection'"
        :value="{
            class: 'Collection',
            elements: props.value.elements,
            identifier: 'Collection',
            type: props.value.collection_type,
        }" />
    <FormExampleDataElement
        v-else-if="props.value.class === 'File'"
        :value="{
            class: 'File',
            identifier: 'Dataset',
            location: props.value.location,
        }"
        :file-type="props.value.filetype" />
</template>
