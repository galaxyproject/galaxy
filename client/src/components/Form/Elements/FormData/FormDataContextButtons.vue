<script setup lang="ts">
import { faFolder } from "@fortawesome/free-regular-svg-icons";
import { faEye, faPlus, faSpinner, faTimes, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BButtonGroup, BDropdown, BDropdownItem } from "bootstrap-vue";
import { computed } from "vue";
import localize from "@/utils/localization";

import type { CollectionType } from "@/api/datasetCollections";
import {
    COLLECTION_TYPE_TO_LABEL,
    type CollectionBuilderType,
} from "@/components/History/adapters/buildCollectionModal";
import { capitalizeFirstLetter } from "@/utils/strings";

import { buildersForCollectionTypes, unconstrainedCollectionTypeBuilders } from "./collections";
import type { VariantInterface } from "./variants";

const props = defineProps<{
    variant?: VariantInterface[];
    currentField?: number;
    canBrowse?: boolean;
    loading?: boolean;
    workflowRun?: boolean;
    workflowTab: string;
    compact?: boolean;
    collectionTypes?: string[];
    currentSource?: string;
    isPopulated?: boolean;
    showFieldOptions?: boolean;
    showViewCreateOptions?: boolean;
}>();

const emit = defineEmits<{
    (e: "on-browse"): void;
    (e: "set-current-field", value: number): void;
    (e: "update:workflow-tab", value: string): void;
    (e: "create-collection-type", value: CollectionType): void;
}>();

const createTitle = computed(() => {
    const defaultBuilderType = defaultCollectionBuilderType.value;
    return sourceIsCollection.value
        ? `Create a new ${COLLECTION_TYPE_TO_LABEL[defaultBuilderType]}`
        : "Upload dataset(s)";
});

function clickedTab(tab: string) {
    emit("update:workflow-tab", props.workflowTab === tab ? "" : tab);
}

function createCollectionType(colType: CollectionBuilderType) {
    emit("create-collection-type", colType);
    emit("update:workflow-tab", "create");
}

const sourceIsCollection = computed(() => {
    return props.currentSource === "hdca";
});

const availableCollectionBuilders = computed(() => {
    if (props.collectionTypes && props.collectionTypes.length > 0) {
        return buildersForCollectionTypes(props.collectionTypes);
    } else {
        return unconstrainedCollectionTypeBuilders;
    }
});

const hasSingleAvailableCollectionBuilderType = computed(() => {
    return availableCollectionBuilders.value.length === 1;
});

const defaultCollectionBuilderType = computed<CollectionBuilderType>(() => {
    if (availableCollectionBuilders.value.length > 0) {
        return availableCollectionBuilders.value[0] as CollectionBuilderType;
    } else {
        return "list";
    }
});
</script>

<template>
    <BButtonGroup :vertical="!props.compact" buttons class="align-self-start">
        <BButtonGroup
            v-if="props.showFieldOptions && props.variant && props.variant.length > 1"
            buttons
            class="align-self-start">
            <BButton
                v-for="(v, index) in props.variant"
                :key="index"
                v-b-tooltip.hover.bottom
                :pressed="props.currentField === index"
                :title="localize(v.tooltip)"
                :style="v.icon === faFolder && v.multiple ? 'padding: 2px' : ''"
                @click="emit('set-current-field', index)">
                <span v-if="v.icon === faFolder && v.multiple" class="fa-stack" style="height: unset">
                    <FontAwesomeIcon :icon="faFolder" class="fa-stack-1x" />
                    <FontAwesomeIcon :icon="faFolder" class="fa-stack-1x" style="transform: translate(0.2em, -0.2em)" />
                </span>
                <FontAwesomeIcon v-else :icon="v.icon" />
            </BButton>
            <BButton
                v-if="props.canBrowse && !props.workflowRun"
                v-b-tooltip.hover.bottom
                :title="localize('Browse or Upload Datasets')"
                @click="emit('on-browse')">
                <FontAwesomeIcon v-if="props.loading" :icon="faSpinner" spin />
                <span v-else class="font-weight-bold">...</span>
            </BButton>
        </BButtonGroup>
        <BButton
            v-if="props.showViewCreateOptions && props.isPopulated"
            v-b-tooltip.bottom.hover.noninteractive
            class="d-flex flex-gapx-1 align-items-center"
            title="View currently selected"
            :pressed="props.workflowTab === 'view'"
            @click="clickedTab('view')">
            <FontAwesomeIcon :icon="faEye" />
            <span v-if="!props.compact" v-localize>View</span>
        </BButton>
        <!-- three options here - source is a collection that has multiple builders exposed, source is a collection
             that has a single builder exposed, or source is dataset(s). -->
        <template v-if="props.showViewCreateOptions && sourceIsCollection && !hasSingleAvailableCollectionBuilderType">
            <BDropdown
                v-b-tooltip.bottom.hover.noninteractive
                class="d-flex"
                data-description="upload"
                :title="createTitle"
                split
                text="Create"
                @click="createCollectionType(defaultCollectionBuilderType)">
                <BDropdownItem
                    v-for="colType in availableCollectionBuilders"
                    :key="colType"
                    @click="createCollectionType(colType)">
                    {{ capitalizeFirstLetter(COLLECTION_TYPE_TO_LABEL[colType] || "collection") }}
                </BDropdownItem>
            </BDropdown>
            <BButton
                v-if="props.workflowTab === 'create'"
                v-b-tooltip.bottom.hover.noninteractive
                title="Hide Collection Creator"
                variant="link"
                @click="emit('update:workflow-tab', '')">
                <FontAwesomeIcon :icon="faTimes" />
                <span class="sr-only">Close Collection Creator</span>
            </BButton>
        </template>
        <BButton
            v-else-if="props.showViewCreateOptions && sourceIsCollection"
            v-b-tooltip.bottom.hover.noninteractive
            class="d-flex flex-gapx-1 align-items-center"
            data-description="upload"
            :title="createTitle"
            :pressed="props.workflowTab === 'create'"
            @click="clickedTab('create')">
            <FontAwesomeIcon :icon="faPlus" />
            <span v-localize>Create</span>
        </BButton>
        <BButton
            v-else-if="props.showViewCreateOptions && !sourceIsCollection"
            v-b-tooltip.bottom.hover.noninteractive
            class="d-flex flex-gapx-1 align-items-center"
            data-description="upload"
            :title="createTitle"
            :pressed="props.workflowTab === 'create'"
            @click="clickedTab('create')">
            <FontAwesomeIcon :icon="faUpload" />
            <span v-localize>Upload</span>
        </BButton>
    </BButtonGroup>
</template>
