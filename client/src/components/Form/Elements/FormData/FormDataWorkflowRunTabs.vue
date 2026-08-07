<script setup lang="ts">
import { faEye, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, nextTick, ref, watch } from "vue";

import type { HDCASummary } from "@/api";
import type { CollectionBuilderType } from "@/components/Collections/common/buildCollectionModal";
import type { UploadedDataset, UploadModalConfig } from "@/components/Panels/Upload/uploadModalTypes";
import { toDataOptions } from "@/composables/upload/useUploadMethodModal";
import { useHistoryStore } from "@/stores/historyStore";

import type { DataOption, ExtendedCollectionType } from "./types";
import type { VariantInterface } from "./variants";

import CollectionCreatorIndex from "@/components/Collections/CollectionCreatorIndex.vue";
import Heading from "@/components/Common/Heading.vue";
import GenericItem from "@/components/History/Content/GenericItem.vue";
import UploadMethodViewInline from "@/components/Panels/Upload/UploadMethodViewInline.vue";

const WorkflowRunTabs: Record<string, number> = {
    view: 0,
    upload: 1,
    create: 2,
};

const props = defineProps<{
    currentVariant?: VariantInterface | null;
    currentValue?: DataOption[];
    canBrowse?: boolean;
    extensions?: string[];
    collectionType?: CollectionBuilderType;
    stepTitle?: string;
    workflowTab: string;
    extendedCollectionType: ExtendedCollectionType;
}>();

const emit = defineEmits<{
    (e: "focus"): void;
    (e: "uploaded-data", data: DataOption[]): void;
    (e: "update:workflow-tab", value: string): void;
}>();

const currentWorkflowTab = computed({
    get: () => WorkflowRunTabs[props.workflowTab] ?? -1,
    set: (value) => {
        emit("update:workflow-tab", Object.keys(WorkflowRunTabs).find((key) => WorkflowRunTabs[key] === value) || "");
    },
});

const { currentHistoryId } = storeToRefs(useHistoryStore());

const uploadConfig = computed<UploadModalConfig>(() => ({
    formats: props.extensions,
    multiple: props.currentVariant?.multiple,
    allowCollections: false,
    hideTips: true,
    targetHistoryId: currentHistoryId.value ?? undefined,
}));

function addUploadedFiles(value: DataOption[], viewUploads = true) {
    emit("uploaded-data", value);
    if (viewUploads) {
        goToFirstWorkflowTab();
    }
}

function onUploaded(datasets: UploadedDataset[]) {
    const dataOptions = toDataOptions(datasets);
    addUploadedFiles(dataOptions, true);
}

function onUploadCancelled() {
    goToFirstWorkflowTab();
}

function collectionCreated(collection: HDCASummary) {
    const dataOption: DataOption = {
        id: collection.id,
        name: collection.name ?? "",
        src: "hdca",
        keep: true,
        batch: false,
        tags: [],
    };
    addUploadedFiles([dataOption], false);
    emit("focus");
}

const creatorIndex = ref();

function goToFirstWorkflowTab() {
    emit("focus");
    currentWorkflowTab.value = WorkflowRunTabs.view;
}

// hack for AG grid - it doesn't resize automatically so we need to force it
// to resize when the tab has a window
watch(
    currentWorkflowTab,
    () => {
        nextTick(() => {
            if (creatorIndex.value && currentWorkflowTab.value === WorkflowRunTabs.create) {
                creatorIndex.value.redrawCreator();
            }
        });
    },
    { immediate: true },
);
</script>

<template>
    <div>
        <div v-show="currentWorkflowTab === WorkflowRunTabs.view && currentValue">
            <Heading separator size="sm">
                <FontAwesomeIcon :icon="faEye" fixed-width />
                View selected {{ props.currentVariant?.tooltip.toLocaleLowerCase() || "value(s)" }}
            </Heading>
            <div v-for="item in currentValue" :key="item.id">
                <GenericItem class="mr-2 w-100" :item-id="item.id" :item-src="item.src" />
            </div>
        </div>

        <div v-show="currentWorkflowTab === WorkflowRunTabs.upload">
            <Heading separator size="sm">
                <FontAwesomeIcon :icon="faUpload" fixed-width />
                Upload dataset{{ props.currentVariant?.multiple ? "s" : "" }}
            </Heading>
            <UploadMethodViewInline :config="uploadConfig" @uploaded="onUploaded" @cancelled="onUploadCancelled" />
        </div>

        <div v-show="currentWorkflowTab === WorkflowRunTabs.create && props.currentVariant?.src === 'hdca'">
            <CollectionCreatorIndex
                v-if="currentHistoryId && props.collectionType"
                ref="creatorIndex"
                :history-id="currentHistoryId"
                :collection-type="props.collectionType"
                show
                not-modal
                :extensions="props.extensions && props.extensions.filter((ext) => ext !== 'data')"
                :suggested-name="props.stepTitle"
                :extended-collection-type="extendedCollectionType"
                @created-collection="collectionCreated"
                @on-hide="goToFirstWorkflowTab" />
        </div>
    </div>
</template>
