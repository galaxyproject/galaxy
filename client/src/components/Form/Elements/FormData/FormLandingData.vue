<script setup lang="ts">
import type { LandingData } from "./types";

import FormLandingDataElement from "./FormLandingDataElement.vue";

const props = defineProps<{
    value: LandingData;
}>();
</script>

<template>
    <FormLandingDataElement
        v-if="props.value.class === 'Collection'"
        :value="{
            class: 'Collection',
            elements: props.value.elements,
            identifier: 'Collection',
            type: props.value.collection_type,
        }" />
    <FormLandingDataElement
        v-else-if="props.value.class === 'File'"
        :value="{
            class: 'File',
            identifier: 'Dataset',
            location: props.value.location,
        }"
        :file-type="props.value.filetype" />
</template>
