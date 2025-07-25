<script setup lang="ts">
import { computed } from "vue";

import type { HDCASummary } from "@/api";

import { JobStateSummary } from "./JobStateSummary";

import CollectionProgress from "./CollectionProgress.vue";

interface Props {
    hdca: HDCASummary;
}

const props = defineProps<Props>();

const labels = new Map([
    ["list", "list"],
    ["list:paired", "list"],
    ["list:paired_or_unpaired", "list"],
    ["list:list", "list"],
    ["paired", "pair"],
    ["sample_sheet", "sample sheet"],
]);

const jobStateSummary = computed(() => {
    return new JobStateSummary(props.hdca);
});

const collectionLabel = computed(() => {
    const collectionType = props.hdca.collection_type;
    return labels.get(collectionType) ?? "nested list";
});
const hasSingleElement = computed(() => {
    return props.hdca.element_count === 1;
});
const isHomogeneous = computed(() => {
    return props.hdca.elements_datatypes.length === 1;
});
const homogeneousDatatype = computed(() => {
    return isHomogeneous.value ? ` ${props.hdca.elements_datatypes[0]}` : "";
});
const pluralizedItem = computed(() => {
    if (props.hdca.collection_type === "list:list") {
        return pluralize("list");
    }
    if (props.hdca.collection_type === "list:paired" || props.hdca.collection_type === "sample_sheet:paired") {
        return pluralize("pair");
    }
    if (
        props.hdca.collection_type === "list:paired_or_unpaired" ||
        props.hdca.collection_type === "sample_sheet:paired_or_unpaired"
    ) {
        if (!hasSingleElement.value) {
            return "paired and unpaired datasets";
        } else {
            return "dataset pair or unpaired dataset";
        }
    }
    if (props.hdca.collection_type === "paired_or_unpaired") {
        if (!hasSingleElement.value) {
            return "dataset pair";
        } else {
            return "unpaired dataset";
        }
    }
    if (!labels.has(props.hdca.collection_type)) {
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
        <span v-if="hdca.collection_type == 'paired_or_unpaired'" class="description mt-1 mb-1">
            a <b v-if="isHomogeneous">{{ homogeneousDatatype }}</b> {{ pluralizedItem }}
        </span>
        <span v-else class="description mt-1 mb-1">
            a {{ collectionLabel }} with {{ hdca.element_count || 0
            }}<b v-if="isHomogeneous">{{ homogeneousDatatype }}</b> {{ pluralizedItem }}
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
