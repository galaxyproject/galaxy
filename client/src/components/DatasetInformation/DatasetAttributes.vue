<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBars, faCog, faDatabase, faExchangeAlt, faRedo, faSave, faUser } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BTab, BTabs } from "bootstrap-vue";
import { ref } from "vue";

import { DatasetAttributesProvider } from "@/components/providers/DatasetProvider";
import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";

import { setAttributes } from "./services";

import FormDisplay from "@/components/Form/FormDisplay.vue";

library.add(faBars, faCog, faDatabase, faExchangeAlt, faRedo, faSave, faUser);

interface Props {
    datasetId: string;
}

const props = defineProps<Props>();

const historyStore = useHistoryStore();

const messageText = ref("");
const messageVariant = ref("danger");
const formData = ref<Record<string, any>>({});

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

function submit(key: string, operation: string) {
    setAttributes(props.datasetId, formData.value[key], operation).then((response) => {
        messageText.value = response.message;
        messageVariant.value = response.status;

        historyStore.loadCurrentHistory();
    }, onError);
}
</script>

<template>
    <div aria-labelledby="dataset-attributes-heading">
        <h1 id="dataset-attributes-heading" v-localize class="h-lg">Edit Dataset Attributes</h1>

        <BAlert v-if="messageText" class="dataset-attributes-alert" :variant="messageVariant" show>
            {{ localize(messageText) }}
        </BAlert>

        <DatasetAttributesProvider :id="datasetId" v-slot="{ result, loading }" @error="onError">
            <div v-if="!loading" class="mt-3">
                <BTabs>
                    <BTab v-if="!result['attribute_disable']">
                        <template v-slot:title>
                            <FontAwesomeIcon :icon="faBars" class="mr-1" />
                            {{ localize("Attributes") }}
                        </template>

                        <FormDisplay :inputs="result['attribute_inputs']" @onChange="onAttribute" />

                        <div class="mt-2">
                            <BButton
                                id="dataset-attributes-default-save"
                                variant="primary"
                                class="mr-1"
                                @click="submit('attribute', 'attributes')">
                                <FontAwesomeIcon :icon="faSave" class="mr-1" />
                                {{ localize("Save") }}
                            </BButton>

                            <BButton v-if="!result['metadata_disable']" @click="submit('attribute', 'autodetect')">
                                <FontAwesomeIcon :icon="faRedo" class="mr-1" />
                                {{ localize("Auto-detect") }}
                            </BButton>
                        </div>
                    </BTab>

                    <BTab
                        v-if="
                            (!result['conversion_disable'] || !result['datatype_disable']) &&
                            !result['metadata_disable']
                        ">
                        <template v-slot:title>
                            <FontAwesomeIcon :icon="faDatabase" class="mr-1" />
                            {{ localize("Datatypes") }}
                        </template>

                        <div v-if="!result['datatype_disable']" class="ui-portlet-section">
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
                                <FormDisplay :inputs="result['datatype_inputs']" @onChange="onDatatype" />

                                <div class="mt-2">
                                    <BButton variant="primary" class="mr-1" @click="submit('datatype', 'datatype')">
                                        <FontAwesomeIcon :icon="faSave" class="mr-1" />
                                        {{ localize("Save") }}
                                    </BButton>

                                    <BButton @click="submit('datatype', 'datatype_detect')">
                                        <FontAwesomeIcon :icon="faRedo" class="mr-1" />
                                        {{ localize("Auto-detect") }}
                                    </BButton>
                                </div>
                            </div>
                        </div>

                        <div v-if="!result['conversion_disable']" class="ui-portlet-section">
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
                                <FormDisplay :inputs="result['conversion_inputs']" @onChange="onConversion" />

                                <div class="mt-2">
                                    <BButton variant="primary" @click="submit('conversion', 'conversion')">
                                        <FontAwesomeIcon :icon="faExchangeAlt" class="mr-1" />
                                        {{ localize("Create Dataset") }}
                                    </BButton>
                                </div>
                            </div>
                        </div>
                    </BTab>

                    <BTab v-if="!result['permission_disable']">
                        <template v-slot:title>
                            <FontAwesomeIcon :icon="faUser" class="mr-1" />
                            {{ localize("Permissions") }}
                        </template>

                        <FormDisplay :inputs="result['permission_inputs']" @onChange="onPermission" />

                        <div class="mt-2">
                            <BButton variant="primary" @click="submit('permission', 'permission')">
                                <FontAwesomeIcon :icon="faSave" class="mr-1" />
                                {{ localize("Save") }}
                            </BButton>
                        </div>
                    </BTab>
                </BTabs>
            </div>
        </DatasetAttributesProvider>
    </div>
</template>
