<script setup lang="ts">
import { computed } from "vue";

import { type JobStateSummary } from "./JobStateSummary";

import CollectionProgress from "./CollectionProgress.vue";

interface Props {
    elementCount?: number;
    elementsDatatypes?: string[];
    jobStateSummary: JobStateSummary;
    collectionType: string;
}

const props = withDefaults(defineProps<Props>(), {
    elementCount: undefined,
    elementsDatatypes: undefined,
});

const labels = new Map([
    ["list", "list"],
    ["list:paired", "list"],
    ["list:list", "list"],
    ["paired", "pair"],
]);

const collectionLabel = computed(() => {
    return labels.get(props.collectionType) ?? "nested list";
});
const hasSingleElement = computed(() => {
    return props.elementCount === 1;
});
const isHomogeneous = computed(() => {
    return props.elementsDatatypes?.length === 1;
});
const homogeneousDatatype = computed(() => {
    return isHomogeneous.value ? ` ${props.elementsDatatypes?.[0]}` : "";
});
const pluralizedItem = computed(() => {
    if (props.collectionType === "list:list") {
        return pluralize("list");
    }
    if (props.collectionType === "list:paired") {
        return pluralize("pair");
    }
    if (!labels.has(props.collectionType)) {
        return pluralize("dataset collection");
    }
    return pluralize("dataset");
});

function pluralize(word: string) {
    return hasSingleElement.value ? word : `${word}s`;
}
</script>

<template>
    <div>
        <span class="description mt-1 mb-1">
            a {{ collectionLabel }} with {{ elementCount || 0 }}<b>{{ homogeneousDatatype }}</b> {{ pluralizedItem }}
        </span>

        <CollectionProgress v-if="jobStateSummary.size != 0" :summary="jobStateSummary" />
    </div>
</template>

<style lang="scss" scoped>
@import "scss/theme/blue.scss";

.description {
    font-size: $h6-font-size;
}
</style>
