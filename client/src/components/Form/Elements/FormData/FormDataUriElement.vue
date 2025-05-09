<script setup lang="ts">
import { BCollapse, BLink } from "bootstrap-vue";
import { ref } from "vue";

import { type DataUriCollectionElement, isDataUriCollectionElementCollection } from "./types";

const props = defineProps<{
    value: DataUriCollectionElement;
}>();

const expanded = ref(false);
</script>

<template>
    <div v-if="isDataUriCollectionElementCollection(props.value)" data-description="uri element collection">
        <div
            tabindex="0"
            role="button"
            class="form-example-data-element rounded"
            @click="expanded = !expanded"
            @keydown.enter="expanded = !expanded">
            <strong>{{ props.value.identifier || "Collection" }}</strong>
            <i v-if="props.value.collection_type">({{ props.value.collection_type }})</i>
            <span class="float-right"> {{ expanded ? "Hide" : "Show" }} elements </span>
        </div>
        <BCollapse :visible="expanded" class="pl-2">
            <FormDataUriElement v-for="(element, index) in props.value.elements" :key="index" :value="element" />
        </BCollapse>
    </div>
    <div v-else data-description="uri element file">
        <div class="form-example-data-element rounded d-flex justify-content-between align-items-center w-100">
            <div class="w-50">
                <strong data-description="uri element identifier">{{ props.value.identifier || "Dataset" }}</strong>
                <i v-if="props.value.ext" data-description="uri element ext">({{ props.value.ext }})</i>
            </div>
            <BLink
                v-if="props.value.location"
                class="location-link w-50"
                :href="props.value.location"
                target="_blank"
                data-description="uri location">
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

    .location-link {
        text-align: right;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
}
</style>
