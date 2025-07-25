<script setup lang="ts">
import { faEye, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, nextTick, ref, watch } from "vue";

import type { HDCASummary } from "@/api";
import type { CollectionBuilderType } from "@/components/History/adapters/buildCollectionModal";
import { useUploadConfigurations } from "@/composables/uploadConfigurations";
import { useHistoryStore } from "@/stores/historyStore";

import type { DataOption } from "./types";
import type { VariantInterface } from "./variants";

import CollectionCreatorIndex from "@/components/Collections/CollectionCreatorIndex.vue";
import CollectionCreatorShowExtensions from "@/components/Collections/common/CollectionCreatorShowExtensions.vue";
import Heading from "@/components/Common/Heading.vue";
import GenericItem from "@/components/History/Content/GenericItem.vue";
import DefaultBox from "@/components/Upload/DefaultBox.vue";

const WorkflowRunTabs: Record<string, number> = {
    view: 0,
    create: 1,
};

const props = defineProps<{
    currentVariant?: VariantInterface | null;
    currentValue?: DataOption[];
    canBrowse?: boolean;
    extensions?: string[];
    collectionType?: CollectionBuilderType;
    stepTitle?: string;
    workflowTab: string;
}>();

const emit = defineEmits<{
    (e: "focus"): void;
    (e: "uploaded-data", data: any): void;
    (e: "update:workflow-tab", value: string): void;
}>();

const currentWorkflowTab = computed({
    get: () => WorkflowRunTabs[props.workflowTab],
    set: (value) => {
        emit("update:workflow-tab", Object.keys(WorkflowRunTabs).find((key) => WorkflowRunTabs[key] === value) || "");
    },
});

const { currentHistoryId } = storeToRefs(useHistoryStore());

// Upload properties
const {
    configOptions,
    effectiveExtensions,
    listDbKeys,
    ready: uploadReady,
} = useUploadConfigurations(props.extensions);

function addUploadedFiles(value: any[], viewUploads = true) {
    emit("uploaded-data", value);
    if (viewUploads) {
        goToFirstWorkflowTab();
    }
}

function collectionCreated(collection: HDCASummary) {
    addUploadedFiles([collection], false);
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
            if (creatorIndex.value) {
                creatorIndex.value.redrawCreator();
            }
        });
    },
    { immediate: true }
);

// TODO:
// - Add support for the browse files option we have in FormData
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
        <div
            v-show="
                props.canBrowse && props.currentVariant?.src !== 'hdca' && currentWorkflowTab === WorkflowRunTabs.create
            ">
            <Heading separator size="sm">
                <FontAwesomeIcon :icon="faUpload" fixed-width />
                Upload {{ props.currentVariant?.tooltip.toLocaleLowerCase() || "value(s)" }}
            </Heading>
            <DefaultBox
                v-if="currentHistoryId && uploadReady && configOptions"
                :effective-extensions="effectiveExtensions"
                v-bind="configOptions"
                :has-callback="false"
                :history-id="currentHistoryId"
                :list-db-keys="listDbKeys"
                disable-footer
                emit-uploaded
                size="small"
                @uploaded="addUploadedFiles"
                @dismiss="goToFirstWorkflowTab">
                <template v-slot:footer>
                    <CollectionCreatorShowExtensions
                        :extensions="props.extensions && props.extensions.filter((ext) => ext !== 'data')"
                        upload />
                </template>
            </DefaultBox>
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
                @created-collection="collectionCreated"
                @on-hide="goToFirstWorkflowTab" />
        </div>
    </div>
</template>
