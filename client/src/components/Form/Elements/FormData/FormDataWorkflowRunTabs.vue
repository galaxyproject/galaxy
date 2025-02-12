<script setup lang="ts">
import { faEye, faPlus, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BTab, BTabs } from "bootstrap-vue";
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

const COLLECTION_TYPE_TO_LABEL: Record<string, string> = {
    list: "list",
    "list:paired": "list of dataset pairs",
    paired: "dataset pair",
};

const WorkflowRunTabs: Record<string, number> = {
    view: 0,
    upload: 1,
};

const props = defineProps<{
    currentVariant?: VariantInterface | null;
    currentValue?: DataOption[];
    canBrowse?: boolean;
    extensions?: string[];
    collectionTypes?: CollectionType[];
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

/** Allowed collection types for collection creation */
const effectiveCollectionTypes = props.collectionTypes?.filter((collectionType) =>
    ["list", "list:paired", "paired"].includes(collectionType)
);

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
    emit("focus");
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
    <BTabs v-model="currentWorkflowTab" justified>
        <BTab active>
            <template v-slot:title>
                <FontAwesomeIcon :icon="faEye" fixed-width />
                <span v-localize>View your selected {{ currentVariant?.tooltip.toLocaleLowerCase() }}</span>
            </template>
            <div v-if="currentValue">
                <div v-for="item in currentValue" :key="item.id">
                    <GenericItem class="mr-2 w-100" :item-id="item.id" :item-src="item.src" />
                </div>
            </div>
            <div v-else>
                <BAlert variant="warning" show>
                    <span v-localize>No {{ currentVariant?.tooltip.toLocaleLowerCase() }} selected</span>
                </BAlert>
            </div>
        </BTab>
        <template v-if="canBrowse">
            <BTab>
                <template v-slot:title>
                    <FontAwesomeIcon :icon="faUpload" fixed-width />
                    <span v-localize>Browse or Upload Datasets</span>
                </template>
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
            </BTab>
        </template>
        <template v-if="currentHistoryId && effectiveCollectionTypes && effectiveCollectionTypes?.length > 0">
            <BTab v-for="collectionType in effectiveCollectionTypes" :key="collectionType">
                <template v-slot:title>
                    <FontAwesomeIcon :icon="faPlus" fixed-width />
                    <span v-localize>Create a new {{ COLLECTION_TYPE_TO_LABEL[collectionType] }}</span>
                </template>
                <CollectionCreatorIndex
                    :history-id="currentHistoryId"
                    :collection-type="collectionType"
                    show
                    not-modal
                    :extensions="props.extensions && props.extensions.filter((ext) => ext !== 'data')"
                    @created-collection="collectionCreated"
                    @on-hide="goToFirstWorkflowTab" />
            </BTab>
        </template>
    </BTabs>
</template>
