<script setup lang="ts">
import { faFolder } from "@fortawesome/free-regular-svg-icons";
import { faEye, faPlus, faSpinner, faTimes, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdown, BDropdownItem } from "bootstrap-vue";
import { computed } from "vue";

import type { CollectionType } from "@/api/datasetCollections";
import {
    COLLECTION_TYPE_TO_LABEL,
    type CollectionBuilderType,
} from "@/components/Collections/common/buildCollectionModal";
import type { DataOption } from "@/components/Form/Elements/FormData/types";
import localize from "@/utils/localization";
import { capitalizeFirstLetter } from "@/utils/strings";

import { buildersForCollectionTypes, unconstrainedCollectionTypeBuilders } from "./collections";
import type { VariantInterface } from "./variants";

import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";

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
    extensions?: string[];
    multiple?: boolean;
}>();

const emit = defineEmits<{
    (e: "on-browse"): void;
    (e: "set-current-field", value: number): void;
    (e: "update:workflow-tab", value: string): void;
    (e: "create-collection-type", value: CollectionType): void;
    (e: "uploaded-data", value: DataOption[]): void;
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

function onUpload() {
    emit("update:workflow-tab", "upload");
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
    <GButtonGroup :vertical="!props.compact" class="align-self-start">
        <GButtonGroup
            v-if="props.showFieldOptions && props.variant && props.variant.length > 1"
            class="align-self-start">
            <GButton
                v-for="(v, index) in props.variant"
                :key="index"
                v-g-tooltip.hover.bottom
                :pressed="props.currentField === index"
                :title="localize(v.tooltip)"
                :style="v.icon === faFolder && v.multiple ? 'padding: 2px' : ''"
                @click="emit('set-current-field', index)">
                <span v-if="v.icon === faFolder && v.multiple" class="fa-stack" style="height: unset">
                    <FontAwesomeIcon :icon="faFolder" class="fa-stack-1x" />
                    <FontAwesomeIcon :icon="faFolder" class="fa-stack-1x" style="transform: translate(0.2em, -0.2em)" />
                </span>
                <FontAwesomeIcon v-else :icon="v.icon" />
            </GButton>
            <GButton
                v-if="props.canBrowse && !props.workflowRun"
                v-g-tooltip.hover.bottom
                :title="localize('Browse or Upload Datasets')"
                @click="emit('on-browse')">
                <FontAwesomeIcon v-if="props.loading" :icon="faSpinner" spin />
                <span v-else class="font-weight-bold">...</span>
            </GButton>
        </GButtonGroup>
        <GButton
            v-if="props.showViewCreateOptions && props.isPopulated"
            v-g-tooltip.bottom.hover
            class="d-flex flex-gapx-1 align-items-center"
            title="View currently selected"
            :pressed="props.workflowTab === 'view'"
            @click="clickedTab('view')">
            <FontAwesomeIcon :icon="faEye" />
            <span v-if="!props.compact" v-localize>View</span>
        </GButton>
        <!-- three options here - source is a collection that has multiple builders exposed, source is a collection
             that has a single builder exposed, or source is dataset(s). -->
        <template v-if="props.showViewCreateOptions && sourceIsCollection && !hasSingleAvailableCollectionBuilderType">
            <BDropdown
                v-g-tooltip.bottom.hover
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
            <GButton
                v-if="props.workflowTab === 'create'"
                v-g-tooltip.bottom.hover
                title="Hide Collection Creator"
                transparent
                @click="emit('update:workflow-tab', '')">
                <FontAwesomeIcon :icon="faTimes" />
                <span class="sr-only">Close Collection Creator</span>
            </GButton>
        </template>
        <GButton
            v-else-if="props.showViewCreateOptions && sourceIsCollection"
            v-g-tooltip.bottom.hover
            class="d-flex flex-gapx-1 align-items-center"
            data-description="upload"
            :title="createTitle"
            :pressed="props.workflowTab === 'create'"
            @click="clickedTab('create')">
            <FontAwesomeIcon :icon="faPlus" />
            <span v-localize>Create</span>
        </GButton>
        <template v-else-if="props.showViewCreateOptions && !sourceIsCollection">
            <GButton
                v-g-tooltip.bottom.hover
                class="d-flex flex-gapx-1 align-items-center"
                data-description="upload"
                title="Upload data"
                @click="onUpload">
                <FontAwesomeIcon :icon="faUpload" />
                <span v-localize>Upload</span>
            </GButton>
        </template>
    </GButtonGroup>
</template>
