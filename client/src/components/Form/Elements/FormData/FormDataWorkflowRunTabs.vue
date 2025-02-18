<script setup lang="ts">
import { faEye, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import type { CollectionType } from "@/components/History/adapters/buildCollectionModal";
import { useUploadConfigurations } from "@/composables/uploadConfigurations";
import { useHistoryStore } from "@/stores/historyStore";

import type { DataOption } from "./types";
import type { VariantInterface } from "./variants";

import CollectionCreatorIndex from "@/components/Collections/CollectionCreatorIndex.vue";
import CollectionCreatorShowExtensions from "@/components/Collections/common/CollectionCreatorShowExtensions.vue";
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
    collectionType?: CollectionType;
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

function addUploadedFiles(value: any[]) {
    emit("uploaded-data", value);
    goToFirstWorkflowTab();
}

function collectionCreated(collection: any) {
    addUploadedFiles([collection]);
}

function goToFirstWorkflowTab() {
    emit("focus");
    currentWorkflowTab.value = WorkflowRunTabs.view;
}

// TODO:
// - Add support for the browse files option we have in FormData
</script>

<template>
    <div>
        <div v-show="currentWorkflowTab === WorkflowRunTabs.view && currentValue" class="bordered-container">
            <div class="heading-container d-flex align-items-center flex-gapx-1">
                <FontAwesomeIcon :icon="faEye" fixed-width />
                <h4 class="m-0">View selected {{ props.currentVariant?.tooltip.toLocaleLowerCase() || "value(s)" }}</h4>
            </div>
            <div v-for="item in currentValue" :key="item.id">
                <GenericItem class="mr-2 w-100" :item-id="item.id" :item-src="item.src" />
            </div>
        </div>
        <div
            v-show="
                props.canBrowse && props.currentVariant?.src !== 'hdca' && currentWorkflowTab === WorkflowRunTabs.create
            "
            class="bordered-container">
            <div class="heading-container d-flex align-items-center flex-gapx-1">
                <FontAwesomeIcon :icon="faUpload" fixed-width />
                <h4 class="m-0">Upload {{ props.currentVariant?.tooltip.toLocaleLowerCase() || "value(s)" }}</h4>
            </div>
            <DefaultBox
                v-if="currentHistoryId && uploadReady"
                :effective-extensions="effectiveExtensions"
                v-bind="configOptions"
                :has-callback="false"
                :history-id="currentHistoryId"
                :list-db-keys="listDbKeys"
                disable-footer
                emit-uploaded
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
                :history-id="currentHistoryId"
                :collection-type="props.collectionType"
                show
                not-modal
                :extensions="props.extensions && props.extensions.filter((ext) => ext !== 'data')"
                @created-collection="collectionCreated"
                @on-hide="goToFirstWorkflowTab" />
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.bordered-container {
    border: 2px solid $portlet-bg-color;
    border-radius: 8px;
    padding: 16px;
    position: relative;
}

.heading-container {
    position: absolute;
    top: -12px;
    left: 16px;
    background: $body-bg;
    padding: 0 8px;
}
</style>
