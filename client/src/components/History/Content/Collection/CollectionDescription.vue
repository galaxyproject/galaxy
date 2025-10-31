<script setup lang="ts">
import { faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";
import { computed } from "vue";

import type { HDCASummary } from "@/api";

import { DatasetStateSummary } from "./DatasetStateSummary";
import { JobStateSummary } from "./JobStateSummary";

import CollectionProgress from "./CollectionProgress.vue";
import DatasetProgress from "./DatasetProgress.vue";

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
    ["sample_sheet:paired", "sample sheet"],
    ["sample_sheet:paired_or_unpaired", "sample sheet"],
]);

const jobStateSummary = computed(() => {
    return new JobStateSummary(props.hdca);
});

const datasetStateSummary = computed(() => {
    return new DatasetStateSummary(props.hdca);
});

const collectionLabel = computed(() => {
    const collectionType = props.hdca.collection_type;
    const isList = collectionType.startsWith("list");
    if (labels.get(collectionType)) {
        return labels.get(collectionType);
    } else if (isList) {
        // call everything like list:list:paired or list:list:list a nested list
        return "nested list";
    } else if (collectionType.indexOf(":") > -1) {
        // e.g. paired:paired or paired:list:list
        return "nested collection";
    } else {
        return "collection";
    }
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
        <div class="d-flex justify-content-between align-items-start">
            <div>
                <span v-if="hdca.collection_type == 'paired_or_unpaired'" class="description mt-1 mb-1">
                    a <b v-if="isHomogeneous">{{ homogeneousDatatype }}</b> {{ pluralizedItem }}
                </span>
                <span v-else class="description mt-1 mb-1">
                    a {{ collectionLabel }} with {{ hdca.element_count || 0
                    }}<b v-if="isHomogeneous">{{ homogeneousDatatype }}</b> {{ pluralizedItem }}
                </span>
            </div>

            <BBadge
                v-if="datasetStateSummary.elements_deleted > 0"
                variant="warning"
                class="ml-2"
                :title="`${datasetStateSummary.elements_deleted} deleted ${
                    datasetStateSummary.elements_deleted === 1 ? 'dataset' : 'datasets'
                } in collection`">
                <FontAwesomeIcon :icon="faTrash" /> {{ datasetStateSummary.elements_deleted }} deleted
            </BBadge>
        </div>

        <CollectionProgress v-if="jobStateSummary.size != 0" :summary="jobStateSummary" />
        <DatasetProgress v-else-if="datasetStateSummary.datasetCount > 0" :summary="datasetStateSummary" />
    </div>
</template>

<style lang="scss" scoped>
@import "scss/theme/blue.scss";

.description {
    font-size: $h6-font-size;
}
</style>
