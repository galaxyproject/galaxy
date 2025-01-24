<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBars, faCog, faDatabase, faExchangeAlt, faRedo, faSave, faUser } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { type AxiosError } from "axios";
import { BAlert, BButton, BTab, BTabs } from "bootstrap-vue";
import { onMounted, ref } from "vue";

import { fetchDatasetAttributes } from "@/api/datasets";
import { setAttributes } from "@/components/DatasetInformation/services";
import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";

import Heading from "../Common/Heading.vue";
import FormDisplay from "@/components/Form/FormDisplay.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

library.add(faBars, faCog, faDatabase, faExchangeAlt, faRedo, faSave, faUser);

interface Props {
    datasetId: string;
}

const props = defineProps<Props>();

const historyStore = useHistoryStore();

const loading = ref(false);
const loadingFailed = ref(false);
const messageText = ref<string>();
const messageVariant = ref("danger");
const formData = ref<Record<string, any>>({});
const datasetAttributes = ref<Record<string, any>>({});

function onAttribute(data: object) {
    formData.value["attribute"] = data;
}

function onConversion(data: object) {
    formData.value["conversion"] = data;
}

function onDatatype(data: object) {
    formData.value["datatype"] = data;
}

function onPermission(data: object) {
    formData.value["permission"] = data;
}

function onError(message: string) {
    messageText.value = message;
    messageVariant.value = "danger";
}

async function submit(key: string, operation: string) {
    try {
        const response = await setAttributes(props.datasetId, formData.value[key], operation);

        messageText.value = response.message;
        messageVariant.value = response.status;

        historyStore.loadCurrentHistory();
    } catch (e) {
        const error = e as AxiosError<{ err_msg?: string }>;

        onError(error.response?.data?.err_msg || "Unable to save dataset attributes.");
    }
}

async function loadDatasetAttributes() {
    loading.value = true;

    try {
        const data = await fetchDatasetAttributes(props.datasetId);

        datasetAttributes.value = data;
    } catch (e) {
        const error = e as AxiosError<{ err_msg?: string }>;
        loadingFailed.value = true;
        onError(error.response?.data?.err_msg || "Unable to fetch available dataset attributes.");
    } finally {
        loading.value = false;
    }
}

onMounted(async () => {
    await loadDatasetAttributes();
});
</script>

<template>
    <div aria-labelledby="dataset-attributes-heading">
        <Heading id="dataset-attributes-heading" h1 separator inline size="xl">
            {{ localize("Edit Dataset Attributes") }}
        </Heading>

        <BAlert v-if="messageText" class="dataset-attributes-alert" :variant="messageVariant" show>
            {{ localize(messageText) }}
        </BAlert>

        <BAlert v-if="loading" variant="info" show>
            <LoadingSpan message="Loading dataset attributes..." />
        </BAlert>
        <div v-else-if="!loadingFailed" class="mt-3">
            <BTabs>
                <BTab v-if="!datasetAttributes['attribute_disable']">
                    <template v-slot:title>
                        <FontAwesomeIcon :icon="faBars" class="mr-1" />
                        {{ localize("Attributes") }}
                    </template>

                    <FormDisplay
                        v-if="datasetAttributes['attribute_inputs']"
                        :inputs="datasetAttributes['attribute_inputs']"
                        @onChange="onAttribute" />

                    <div class="mt-2">
                        <BButton
                            id="dataset-attributes-default-save"
                            variant="primary"
                            class="mr-1"
                            @click="submit('attribute', 'attributes')">
                            <FontAwesomeIcon :icon="faSave" class="mr-1" />
                            {{ localize("Save") }}
                        </BButton>

                        <BButton
                            v-if="!datasetAttributes['metadata_disable']"
                            @click="submit('attribute', 'autodetect')">
                            <FontAwesomeIcon :icon="faRedo" class="mr-1" />
                            {{ localize("Auto-detect") }}
                        </BButton>
                    </div>
                </BTab>

                <BTab
                    v-if="
                        (!datasetAttributes['conversion_disable'] || !datasetAttributes['datatype_disable']) &&
                        !datasetAttributes['metadata_disable']
                    "
                    title-link-class="dataset-edit-datatype-tab">
                    <template v-slot:title>
                        <FontAwesomeIcon :icon="faDatabase" class="mr-1" />
                        {{ localize("Datatypes") }}
                    </template>

                    <div v-if="!datasetAttributes['datatype_disable']" class="ui-portlet-section">
                        <div class="portlet-header">
                            <div class="portlet-title">
                                <FontAwesomeIcon :icon="faDatabase" class="portlet-title-icon fa-fw mr-1" />

                                <span class="portlet-title-text">
                                    <b itemprop="name">
                                        {{ localize("Assign Datatype") }}
                                    </b>
                                </span>
                            </div>
                        </div>
                        <div class="portlet-content">
                            <FormDisplay
                                v-if="datasetAttributes['datatype_inputs']"
                                :inputs="datasetAttributes['datatype_inputs']"
                                @onChange="onDatatype" />

                            <div class="mt-2">
                                <BButton variant="primary" class="mr-1" @click="submit('datatype', 'datatype')">
                                    <FontAwesomeIcon :icon="faSave" class="mr-1" />
                                    {{ localize("Save") }}
                                </BButton>

                                <BButton
                                    id="dataset-attributes-autodetect-datatype"
                                    @click="submit('datatype', 'datatype_detect')">
                                    <FontAwesomeIcon :icon="faRedo" class="mr-1" />
                                    {{ localize("Auto-detect") }}
                                </BButton>
                            </div>
                        </div>
                    </div>

                    <div v-if="!datasetAttributes['conversion_disable']" class="ui-portlet-section">
                        <div class="portlet-header">
                            <div class="portlet-title">
                                <FontAwesomeIcon :icon="faCog" class="portlet-title-icon fa-fw mr-1" />

                                <span class="portlet-title-text">
                                    <b itemprop="name">
                                        {{ localize("Convert to Datatype") }}
                                    </b>
                                </span>
                            </div>
                        </div>
                        <div class="portlet-content">
                            <FormDisplay
                                v-if="datasetAttributes['conversion_inputs']"
                                :inputs="datasetAttributes['conversion_inputs']"
                                @onChange="onConversion" />

                            <div class="mt-2">
                                <BButton variant="primary" @click="submit('conversion', 'conversion')">
                                    <FontAwesomeIcon :icon="faExchangeAlt" class="mr-1" />
                                    {{ localize("Create Dataset") }}
                                </BButton>
                            </div>
                        </div>
                    </div>
                </BTab>

                <BTab v-if="!datasetAttributes['permission_disable']">
                    <template v-slot:title>
                        <FontAwesomeIcon :icon="faUser" class="mr-1" />
                        {{ localize("Permissions") }}
                    </template>

                    <FormDisplay
                        v-if="datasetAttributes['permission_inputs']"
                        :inputs="datasetAttributes['permission_inputs']"
                        @onChange="onPermission" />

                    <div class="mt-2">
                        <BButton variant="primary" @click="submit('permission', 'permission')">
                            <FontAwesomeIcon :icon="faSave" class="mr-1" />
                            {{ localize("Save") }}
                        </BButton>
                    </div>
                </BTab>
            </BTabs>
        </div>
    </div>
</template>
