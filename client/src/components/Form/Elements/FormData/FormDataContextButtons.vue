<script setup lang="ts">
import { faFolder } from "@fortawesome/free-regular-svg-icons";
import { faCaretDown, faEye, faPlus, faSpinner, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BButtonGroup, BDropdown, BDropdownItem } from "bootstrap-vue";
import { computed } from "vue";

import { COLLECTION_TYPE_TO_LABEL, type CollectionType } from "@/components/History/adapters/buildCollectionModal";
import { capitalizeFirstLetter } from "@/utils/strings";

import type { VariantInterface } from "./variants";

const props = defineProps<{
    variant?: VariantInterface[];
    currentField?: number;
    canBrowse?: boolean;
    loading?: boolean;
    workflowRun?: boolean;
    workflowTab: string;
    compact?: boolean;
    collectionType?: string;
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
    return props.collectionType
        ? `Create a new ${COLLECTION_TYPE_TO_LABEL[props.collectionType]}`
        : "Upload dataset(s)";
});

function clickedTab(tab: string) {
    emit("update:workflow-tab", props.workflowTab === tab ? "" : tab);
}

function createCollectionType(colType: string) {
    emit("create-collection-type", colType as CollectionType);
    emit("update:workflow-tab", "create");
}
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
                :title="v.tooltip"
                :style="v.icon === faFolder && v.multiple ? 'padding-bottom: 2px' : ''"
                @click="emit('set-current-field', index)">
                <span v-if="v.icon === faFolder && v.multiple" style="position: relative; display: inline-block">
                    <FontAwesomeIcon :icon="faFolder" size="sm" style="position: absolute; left: 2px" />
                    <FontAwesomeIcon :icon="faFolder" size="sm" />
                </span>
                <FontAwesomeIcon v-else :icon="v.icon" />
            </BButton>
            <BButton
                v-if="props.canBrowse && !props.workflowRun"
                v-b-tooltip.hover.bottom
                title="Browse or Upload Datasets"
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
        <BDropdown
            v-if="props.showViewCreateOptions && props.currentSource === 'hdca' && !props.collectionType"
            v-b-tooltip.bottom.hover.noninteractive
            class="d-flex flex-gapx-1 align-items-center"
            title="Create a new collection"
            no-caret
            toggle-class="d-flex flex-gapx-1 align-items-center">
            <template v-slot:button-content>
                <FontAwesomeIcon :icon="faCaretDown" />
                <span v-localize>Create</span>
            </template>
            <BDropdownItem
                v-for="colType in Object.keys(COLLECTION_TYPE_TO_LABEL)"
                :key="colType"
                @click="createCollectionType(colType)">
                {{ capitalizeFirstLetter(COLLECTION_TYPE_TO_LABEL[colType] || "collection") }}
            </BDropdownItem>
        </BDropdown>
        <BButton
            v-else-if="props.showViewCreateOptions"
            v-b-tooltip.bottom.hover.noninteractive
            class="d-flex flex-gapx-1 align-items-center"
            :title="createTitle"
            :pressed="props.workflowTab === 'create'"
            @click="clickedTab('create')">
            <FontAwesomeIcon :icon="!props.collectionType ? faUpload : faPlus" />
            <span v-localize>{{ !props.collectionType ? "Upload" : "Create" }}</span>
        </BButton>
    </BButtonGroup>
</template>
