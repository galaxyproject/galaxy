<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBars, faCog, faDatabase, faTable, faUser } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
import { BAlert, BSpinner, BTab, BTabs } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { copyCollection } from "@/api/datasetCollections";
import { DatatypesProvider, DbKeyProvider, SuitableConvertersProvider } from "@/components/providers";
import { useConfig } from "@/composables/config";
import { useCollectionAttributesStore } from "@/stores/collectionAttributesStore";
import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";
import { prependPath } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import { HistoryContentBulkOperationPayload, updateHistoryItemsBulk } from "./services";

import ChangeDatatypeTab from "@/components/Collections/common/ChangeDatatypeTab.vue";
import DatabaseEditTab from "@/components/Collections/common/DatabaseEditTab.vue";
import SuitableConvertersTab from "@/components/Collections/common/SuitableConvertersTab.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

library.add(faBars, faCog, faDatabase, faTable, faUser);

interface Props {
    collectionId: string;
}

const props = defineProps<Props>();

const { config, isConfigLoaded } = useConfig(true);
const collectionAttributesStore = useCollectionAttributesStore();

const historyStore = useHistoryStore();
const { currentHistoryId } = storeToRefs(historyStore);

const jobError = ref(null);
const errorMessage = ref("");
const infoMessage = ref("This will create a new collection in your History. Your quota will not increase.");

const attributesData = computed(() => {
    return collectionAttributesStore.getAttributes(props.collectionId);
});
const databaseKeyFromElements = computed(() => {
    return attributesData.value?.dbkey;
});
const datatypeFromElements = computed(() => {
    return attributesData.value?.extension;
});

function updateInfoMessage(strMessage: string) {
    infoMessage.value = strMessage;
}

// TODO: Replace with actual datatype type
async function clickedSave(attribute: string, newValue: any) {
    if (attribute !== "dbkey") {
        // TODO: extend this to other attributes that could be changed
        console.error(`Changing ${attribute} not implemented`);
        return;
    }

    const dbKey = newValue.id;

    try {
        await copyCollection(props.collectionId, dbKey);
    } catch (err) {
        errorMessage.value = errorMessageAsString(err, "History import failed.");
    }
}

// TODO: Replace with actual datatype type
async function clickedConvert(selectedConverter: any) {
    const url = prependPath(`/api/tools/${selectedConverter.tool_id}/convert`);
    const data = {
        src: "hdca",
        id: props.collectionId,
        source_type: selectedConverter.original_type,
        target_type: selectedConverter.target_type,
    };

    try {
        await axios.post(url, data).catch(handleError);
    } catch (err) {
        errorMessage.value = errorMessageAsString(err, "History import failed.");
    }
}

// TODO: Replace with actual datatype type
async function clickedDatatypeChange(selectedDatatype: any) {
    const data: HistoryContentBulkOperationPayload = {
        items: [
            {
                history_content_type: "dataset_collection",
                id: props.collectionId,
            },
        ],
        operation: "change_datatype",
        params: {
            type: "change_datatype",
            datatype: selectedDatatype.id,
        },
    };

    try {
        await updateHistoryItemsBulk(currentHistoryId.value ?? "", data);
    } catch (err) {
        errorMessage.value = errorMessageAsString(err, "History import failed.");
    }
}

function handleError(err: any) {
    errorMessage.value = errorMessageAsString(err, "History import failed.");

    if (err?.data?.stderr) {
        jobError.value = err.data;
    }
}
</script>

<template>
    <div aria-labelledby="collection-edit-view-heading">
        <h1 id="collection-edit-view-heading" class="h-lg">{{ localize("Edit Collection Attributes") }}</h1>

        <BAlert show variant="info" dismissible>
            {{ localize(infoMessage) }}
        </BAlert>

        <BAlert v-if="jobError" show variant="danger" dismissible>
            {{ localize(errorMessage) }}
        </BAlert>

        <BTabs content-class="mt-3">
            <BTab
                title-link-class="collection-edit-change-genome-nav"
                @click="
                    updateInfoMessage(
                        'This will create a new collection in your History. Your quota will not increase.'
                    )
                ">
                <template v-slot:title>
                    <FontAwesomeIcon :icon="faTable" />
                    &nbsp; {{ localize("Database/Build") }}
                </template>

                <DbKeyProvider v-slot="{ item, loading }">
                    <div v-if="loading">
                        <BSpinner label="Loading Database/Builds..." />
                    </div>
                    <div v-else>
                        <DatabaseEditTab
                            v-if="item && databaseKeyFromElements"
                            :database-key-from-elements="databaseKeyFromElements"
                            :genomes="item"
                            @clicked-save="clickedSave" />
                    </div>
                </DbKeyProvider>
            </BTab>

            <SuitableConvertersProvider :id="collectionId" v-slot="{ item }">
                <BTab
                    v-if="item && item.length"
                    title-link-class="collection-edit-convert-datatype-nav"
                    @click="updateInfoMessage('This will create a new collection in your History.')">
                    <template v-slot:title>
                        <FontAwesomeIcon :icon="faCog" />
                        &nbsp; {{ localize("Convert") }}
                    </template>

                    <SuitableConvertersTab :suitable-converters="item" @clicked-convert="clickedConvert" />
                </BTab>
            </SuitableConvertersProvider>

            <BTab
                v-if="isConfigLoaded && config.enable_celery_tasks"
                title-link-class="collection-edit-change-datatype-nav"
                @click="
                    updateInfoMessage(
                        'This operation might take a short while, depending on the size of your collection.'
                    )
                ">
                <template v-slot:title>
                    <FontAwesomeIcon :icon="faDatabase" />
                    &nbsp; {{ localize("Datatypes") }}
                </template>

                <DatatypesProvider v-slot="{ item, loading }">
                    <div v-if="loading">
                        <LoadingSpan message="Loading Datatypes" />
                    </div>
                    <div v-else>
                        <ChangeDatatypeTab
                            v-if="item && datatypeFromElements"
                            :datatype-from-elements="datatypeFromElements"
                            :datatypes="item"
                            @clicked-save="clickedDatatypeChange" />
                    </div>
                </DatatypesProvider>
            </BTab>
        </BTabs>
    </div>
</template>
