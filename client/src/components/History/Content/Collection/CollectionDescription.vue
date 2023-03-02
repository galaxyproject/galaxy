<script setup lang="ts">
import CollectionProgress from "./CollectionProgress.vue";
import { computed } from "vue";
import type { JobStateSummary } from "./JobStateSummary";

const props = withDefaults(
    defineProps<{
        jobStateSummary: JobStateSummary;
        collectionType: string;
        elementCount?: number;
        elementsDatatypes?: string[];
    }>(),
    {
        elementsDatatypes: () => [],
    }
);

const labels = new Map([
    ["list", "list"],
    ["list:paired", "list"],
    ["list:list", "list"],
    ["paired", "pair"],
]);

const collectionLabel = computed(() => labels.get(props.collectionType) ?? "nested list");
const hasSingleElement = computed(() => props.elementCount === 1);
const isHomogeneous = computed(() => props.elementsDatatypes.length === 1);
const homogeneousDatatype = computed(() => (isHomogeneous.value ? props.elementsDatatypes[0] : ""));
const pluralizedItem = computed(() => {
    if (props.collectionType === "list:list") {
        return pluralize("list");
    } else if (props.collectionType === "list:paired") {
        return pluralize("pair");
    } else if (labels.has(props.collectionType)) {
        return pluralize("dataset collection");
    } else {
        return pluralize("dataset");
    }
});

function pluralize(word: string): string {
    return hasSingleElement.value ? word : `${word}s`;
}
</script>

<template>
    <div>
        <span class="description mt-1 mb-1">
            a {{ collectionLabel }} with {{ props.elementCount }}<b>{{ homogeneousDatatype }}</b> {{ pluralizedItem }}
        </span>
        <CollectionProgress v-if="props.jobStateSummary.size !== 0" :summary="props.jobStateSummary" />
    </div>
</template>

<style lang="scss" scoped>
@import "scss/theme/blue.scss";

.description {
    font-size: $h6-font-size;
}
</style>
