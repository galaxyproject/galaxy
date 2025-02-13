<script setup lang="ts">
import { faEye, faPlus, faSpinner, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BButtonGroup } from "bootstrap-vue";
import { computed } from "vue";

import { COLLECTION_TYPE_TO_LABEL } from "@/components/History/adapters/buildCollectionModal";

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
    isPopulated?: boolean;
    showFieldOptions?: boolean;
    showViewCreateOptions?: boolean;
}>();

const emit = defineEmits<{
    (e: "on-browse"): void;
    (e: "set-current-field", value: number): void;
    (e: "update:workflow-tab", value: string): void;
}>();

const createTitle = computed(() => {
    return props.collectionType
        ? `Create a new ${COLLECTION_TYPE_TO_LABEL[props.collectionType]}`
        : "Upload dataset(s)";
});

function clickedCreate() {
    emit("update:workflow-tab", props.workflowTab === "create" ? "view" : "create");
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
                @click="emit('set-current-field', index)">
                <FontAwesomeIcon :icon="['far', v.icon]" />
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
            @click="emit('update:workflow-tab', 'view')">
            <FontAwesomeIcon :icon="faEye" />
            <span v-if="!props.compact" v-localize>View</span>
        </BButton>
        <BButton
            v-if="props.showViewCreateOptions"
            v-b-tooltip.bottom.hover.noninteractive
            class="d-flex flex-gapx-1 align-items-center"
            :title="createTitle"
            :pressed="props.workflowTab === 'create'"
            @click="clickedCreate">
            <FontAwesomeIcon :icon="!props.collectionType ? faUpload : faPlus" />
            <span v-localize>{{ !props.collectionType ? "Upload" : "Create" }}</span>
        </BButton>
    </BButtonGroup>
</template>
