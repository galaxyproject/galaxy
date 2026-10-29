<script setup lang="ts">
import { faBurn, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";
import { computed } from "vue";

import type { HDCASummary } from "@/api";
import { findKnownCollectionType } from "@/components/Collections/common/knownCollectionTypes";
import { pluralize } from "@/utils/strings";

import { DatasetStateSummary } from "./DatasetStateSummary";
import { JobStateSummary } from "./JobStateSummary";

import CollectionProgress from "./CollectionProgress.vue";
import DatasetProgress from "./DatasetProgress.vue";

interface Props {
    hdca: HDCASummary;
    /** Leave out the purged count when every element is purged, for hosts that show their own "Purged" badge. */
    hideAllPurgedCount?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    hideAllPurgedCount: false,
});

const knownCollectionType = computed(() => findKnownCollectionType(props.hdca.collection_type));

const typeTitle = computed(() => {
    const known = knownCollectionType.value;
    return known ? `${known.label} (${known.collectionType})` : props.hdca.collection_type;
});

const jobStateSummary = computed(() => {
    return new JobStateSummary(props.hdca);
});

const datasetStateSummary = computed(() => {
    return new DatasetStateSummary(props.hdca);
});

const deletedCount = computed(() => datasetStateSummary.value.deletedNotPurgedCount);
const purgedCount = computed(() => {
    const summary = datasetStateSummary.value;
    return props.hideAllPurgedCount && summary.allElementsPurged ? 0 : summary.elements_purged;
});

const collectionLabel = computed(() => {
    const collectionType = props.hdca.collection_type;
    const isList = collectionType.startsWith("list");
    if (knownCollectionType.value) {
        return knownCollectionType.value.summary.container;
    } else if (isList) {
        // call everything like list:list:list a nested list
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
    if (props.hdca.collection_type === "paired_or_unpaired") {
        if (!hasSingleElement.value) {
            return "dataset pair";
        } else {
            return "unpaired dataset";
        }
    }
    if (knownCollectionType.value) {
        const { element, elementPlural } = knownCollectionType.value.summary;
        return hasSingleElement.value ? element : elementPlural;
    }
    return pluralize(props.hdca.element_count ?? 0, "dataset collection");
});
</script>

<template>
    <div>
        <div class="d-flex justify-content-between align-items-start">
            <div>
                <span v-g-tooltip.hover class="description mt-1 mb-1" :title="typeTitle">
                    <template v-if="hdca.collection_type == 'paired_or_unpaired'">
                        a <b v-if="isHomogeneous">{{ homogeneousDatatype }}</b> {{ pluralizedItem }}
                    </template>
                    <template v-else>
                        a {{ collectionLabel }} with {{ hdca.element_count || 0
                        }}<b v-if="isHomogeneous">{{ homogeneousDatatype }}</b> {{ pluralizedItem }}
                    </template>
                </span>
            </div>

            <div class="d-flex">
                <BBadge
                    v-if="deletedCount > 0"
                    variant="warning"
                    class="deleted-elements ml-2"
                    :title="`${deletedCount} deleted ${pluralize(deletedCount, 'dataset')} in collection`">
                    <FontAwesomeIcon :icon="faTrash" /> {{ deletedCount }} deleted
                </BBadge>
                <BBadge
                    v-if="purgedCount > 0"
                    variant="secondary"
                    class="purged-elements ml-2"
                    :title="`${purgedCount} permanently deleted ${pluralize(purgedCount, 'dataset')} in collection`">
                    <FontAwesomeIcon :icon="faBurn" /> {{ purgedCount }} purged
                </BBadge>
            </div>
        </div>

        <CollectionProgress v-if="jobStateSummary.size != 0" :summary="jobStateSummary" />
        <DatasetProgress v-else-if="datasetStateSummary.datasetCount > 0" :summary="datasetStateSummary" />
    </div>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.description {
    font-size: $h6-font-size;
}
</style>
