<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBars, faCog, faDatabase, faSave, faTable, faUser } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
import { BAlert, BButton, BSpinner, BTab, BTabs } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { copyCollection } from "@/api/datasetCollections";
import { updateContentFields } from "@/components/History/model/queries";
import { DatatypesProvider, DbKeyProvider, SuitableConvertersProvider } from "@/components/providers";
import { useConfig } from "@/composables/config";
import { useCollectionAttributesStore } from "@/stores/collectionAttributesStore";
import { useCollectionElementsStore } from "@/stores/collectionElementsStore";
import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";
import { prependPath } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import { HistoryContentBulkOperationPayload, updateHistoryItemsBulk } from "./services";

import ChangeDatatypeTab from "@/components/Collections/common/ChangeDatatypeTab.vue";
import DatabaseEditTab from "@/components/Collections/common/DatabaseEditTab.vue";
import SuitableConvertersTab from "@/components/Collections/common/SuitableConvertersTab.vue";
import Heading from "@/components/Common/Heading.vue";
import FormDisplay from "@/components/Form/FormDisplay.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

library.add(faBars, faCog, faDatabase, faSave, faTable, faUser);

interface Props {
    collectionId: string;
}

const props = defineProps<Props>();

const { config, isConfigLoaded } = useConfig(true);
const collectionAttributesStore = useCollectionAttributesStore();

const historyStore = useHistoryStore();
const { currentHistoryId } = storeToRefs(historyStore);

const collectionStore = useCollectionElementsStore();

const jobError = ref(null);
const errorMessage = ref("");
const infoMessage = ref("");
const successMessage = ref("");
const attributesInputs = ref<{ name: string; label: string; type: string; value: any }[]>([]);

/** Used to track if there has been a change in the collection, and rerenders `FormDisplay` */
const collectionChangeKey = ref(0);

const attributesData = computed(() => {
    return collectionAttributesStore.getAttributes(props.collectionId);
});

const attributesLoadError = computed(() => {
    const itemLoadError = collectionAttributesStore.getItemLoadError(props.collectionId);
    if (itemLoadError) {
        return errorMessageAsString(itemLoadError);
    }
    return undefined;
});

const collection = computed(() => {
    return collectionStore.getCollectionById(props.collectionId);
});
const collectionLoadError = computed(() => {
    if (collection.value) {
        const collectionElementLoadError = collectionStore.getLoadingCollectionElementsError(collection.value);
        if (collectionElementLoadError) {
            return errorMessageAsString(collectionElementLoadError);
        }
    }
    return undefined;
});
watch([attributesLoadError, collectionLoadError], () => {
    if (attributesLoadError.value) {
        errorMessage.value = attributesLoadError.value;
    } else if (collectionLoadError.value) {
        errorMessage.value = collectionLoadError.value;
    }
});
const databaseKeyFromElements = computed(() => {
    return attributesData.value?.dbkey;
});
const datatypeFromElements = computed(() => {
    return attributesData.value?.extension;
});

watch(
    () => collection.value,
    (newVal) => {
        if (newVal) {
            collectionChangeKey.value++;
            attributesInputs.value = [
                {
                    name: "name",
                    label: "Name",
                    type: "text",
                    value: newVal.name,
                },
            ];
        }
    },
    { immediate: true }
);

function updateInfoMessage(strMessage: string) {
    infoMessage.value = strMessage;
    successMessage.value = "";
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
        errorMessage.value = errorMessageAsString(err, `Changing ${attribute} failed`);
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
        successMessage.value = "Conversion started successfully.";
    } catch (err) {
        errorMessage.value = errorMessageAsString(err, "Conversion failed.");
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
        successMessage.value = "Datatype changed successfully.";
    } catch (err) {
        errorMessage.value = errorMessageAsString(err, "Datatype change failed.");
    }
}

function handleError(err: any) {
    errorMessage.value = errorMessageAsString(err, "Datatype conversion failed.");

    if (err?.data?.stderr) {
        jobError.value = err.data;
    }
}

function onAttribute(data: Record<string, any>) {
    for (const key in data) {
        const index = attributesInputs.value?.findIndex((input) => input.name === key);
        if (index !== -1 && attributesInputs.value[index]) {
            attributesInputs.value[index]!.value = data[key];
        }
    }
}

async function saveAttrs() {
    if (collection.value && attributesInputs.value) {
        const updatedAttrs = attributesInputs.value.reduce((acc, input) => {
            acc[input.name] = input.value;
            return acc;
        }, {} as Record<string, any>);
        try {
            await updateContentFields(collection.value, updatedAttrs);

            successMessage.value = "Attributes updated successfully.";
        } catch (err) {
            errorMessage.value = errorMessageAsString(err, "Unable to update attributes.");
        }
    }
}
</script>

<template>
    <div aria-labelledby="collection-edit-view-heading">
        <Heading id="dataset-attributes-heading" h1 separator inline size="xl">
            {{ localize("Edit Collection Attributes") }}
        </Heading>

        <BAlert v-if="infoMessage" show variant="info" dismissible>
            {{ localize(infoMessage) }}
        </BAlert>

        <BAlert v-if="errorMessage" show variant="danger">
            {{ localize(errorMessage) }}
        </BAlert>

        <BAlert v-if="successMessage" show variant="success" dismissible>
            {{ localize(successMessage) }}
        </BAlert>
        <BTabs v-if="!errorMessage" class="mt-3">
            <BTab title-link-class="collection-edit-attributes-nav" @click="updateInfoMessage('')">
                <template v-slot:title>
                    <FontAwesomeIcon :icon="faBars" class="mr-1" />
                    {{ localize("Attributes") }}
                </template>

                <FormDisplay
                    v-if="attributesInputs.length > 0"
                    :key="collectionChangeKey"
                    :inputs="attributesInputs"
                    @onChange="onAttribute" />

                <div class="mt-2">
                    <BButton id="dataset-attributes-default-save" variant="primary" @click="saveAttrs">
                        <FontAwesomeIcon :icon="faSave" class="mr-1" />
                        {{ localize("Save") }}
                    </BButton>
                </div>
            </BTab>
            <BTab
                title-link-class="collection-edit-change-genome-nav"
                @click="
                    updateInfoMessage(
                        'This will create a new collection in your History. Your quota will not increase.'
                    )
                ">
                <template v-slot:title>
                    <FontAwesomeIcon :icon="faTable" class="mr-1" />
                    {{ localize("Database/Build") }}
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
                        <FontAwesomeIcon :icon="faCog" class="mr-1" />
                        {{ localize("Convert") }}
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
                    <FontAwesomeIcon :icon="faDatabase" class="mr-1" />
                    {{ localize("Datatypes") }}
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
