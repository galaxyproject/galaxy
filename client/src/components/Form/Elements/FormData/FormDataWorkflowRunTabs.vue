<script setup lang="ts">
import { faEye, faPlus, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BTab, BTabs } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { useConfig } from "@/composables/config";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import type { DataOption } from "./types";
import type { VariantInterface } from "./variants";

import CollectionCreatorIndex from "@/components/Collections/CollectionCreatorIndex.vue";
import GenericItem from "@/components/History/Content/GenericItem.vue";
import UploadContainer from "@/components/Upload/UploadContainer.vue";

const COLLECTION_TYPE_TO_LABEL: Record<string, string> = {
    list: "list",
    "list:paired": "list of dataset pairs",
    paired: "dataset pair",
};

const WorkflowRunTabs = {
    view: 0,
};

const props = defineProps<{
    currentVariant?: VariantInterface | null;
    currentValue?: DataOption[];
    canBrowse?: boolean;
    extensions?: string[];
    collectionTypes?: string[];
}>();

const emit = defineEmits<{
    (e: "focus"): void;
    (e: "created-collection", collection: Record<string, any>): void;
}>();

const currentWorkflowTab = ref(WorkflowRunTabs.view);

/** Allowed collection types for collection creation */
const effectiveCollectionTypes = props.collectionTypes?.filter((collectionType) =>
    ["list", "list:paired", "paired"].includes(collectionType)
);

const { currentHistoryId } = storeToRefs(useHistoryStore());
const { currentUser } = storeToRefs(useUserStore());

// Upload properties
const { config, isConfigLoaded } = useConfig();

const configOptions = computed(() =>
    isConfigLoaded.value
        ? {
              chunkUploadSize: config.value.chunk_upload_size,
              fileSourcesConfigured: config.value.file_sources_configured,
              ftpUploadSite: config.value.ftp_upload_site,
              defaultDbKey: config.value.default_genome || "",
              defaultExtension: config.value.default_extension || "",
          }
        : {}
);

function collectionCreated(collection: Record<string, any>) {
    emit("created-collection", collection);
    emit("focus");
}

function goToFirstWorkflowTab() {
    emit("focus");
    currentWorkflowTab.value = WorkflowRunTabs.view;
}

// TODO:
// - Add support for emitting upload data from the UploadContainer tab (multiple files as well)
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
                <UploadContainer
                    v-if="currentHistoryId && currentUser && 'id' in currentUser"
                    :current-user-id="currentUser?.id"
                    :current-history-id="currentHistoryId"
                    :multiple="false"
                    v-bind="configOptions"
                    @dismiss="goToFirstWorkflowTab" />
            </BTab>
        </template>
        <template v-if="effectiveCollectionTypes && effectiveCollectionTypes?.length > 0">
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
