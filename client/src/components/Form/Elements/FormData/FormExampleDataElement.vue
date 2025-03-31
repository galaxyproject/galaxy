<script setup lang="ts">
import { BCollapse, BLink } from "bootstrap-vue";
import { ref } from "vue";

import type { ExampleDataCollectionElement, ExampleDataFileElement } from "./types";

const props = defineProps<{
    value: ExampleDataCollectionElement | ExampleDataFileElement;
    fileType?: string;
}>();

const expanded = ref(false);
</script>

<template>
    <div v-if="props.value.class === 'Collection'">
        <div
            tabindex="0"
            role="button"
            class="form-example-data-element rounded"
            @click="expanded = !expanded"
            @keydown.enter="expanded = !expanded">
            <strong>{{ props.value.identifier || "Collection" }}</strong>
            <i>({{ props.value.type }})</i>
            <span class="float-right"> {{ expanded ? "Hide" : "Show" }} elements </span>
        </div>
        <BCollapse :visible="expanded" class="pl-2">
            <FormExampleDataElement v-for="(element, index) in props.value.elements" :key="index" :value="element" />
        </BCollapse>
    </div>
    <div v-else-if="props.value.class === 'File'">
        <div class="form-example-data-element rounded d-flex justify-content-between align-items-center w-100">
            <div>
                <strong>{{ props.value.identifier || "Dataset" }}</strong>
                <i v-if="props.fileType">({{ props.fileType }})</i>
            </div>
            <BLink v-if="props.value.location" :href="props.value.location" target="_blank">
                <i>{{ props.value.location }}</i>
            </BLink>
        </div>
    </div>
</template>

<style scoped lang="scss">
.form-example-data-element {
    // background-color: $state-success-bg; // TODO: Does not seem to work even
    //                                              with the "theme/blue.scss" import
    background-color: #c2ebc2;
    padding: 0.5rem 1.25rem;
}
</style>
