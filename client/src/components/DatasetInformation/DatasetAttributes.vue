<template>
    <div aria-labelledby="dataset-attributes-heading">
        <h1 id="dataset-attributes-heading" v-localize class="h-lg">Edit Dataset Attributes</h1>
        <b-alert v-if="messageText" class="dataset-attributes-alert" :variant="messageVariant" show>
            {{ messageText | l }}
        </b-alert>
        <DatasetAttributesProvider :id="datasetId" v-slot="{ result, loading }" @error="onError">
            <div v-if="!loading && !hasError" class="mt-3">
                <b-tabs>
                    <b-tab v-if="!result['attribute_disable']">
                        <template v-slot:title>
                            <FontAwesomeIcon icon="bars" class="mr-1" />{{ "Attributes" | l }}
                        </template>
                        <FormDisplay :inputs="result['attribute_inputs']" @onChange="onAttribute" />
                        <div class="mt-2">
                            <b-button
                                id="dataset-attributes-default-save"
                                variant="primary"
                                class="mr-1"
                                @click="submit('attribute', 'attributes')">
                                <FontAwesomeIcon icon="save" class="mr-1" />{{ "Save" | l }}
                            </b-button>
                            <b-button v-if="!result['metadata_disable']" @click="submit('attribute', 'autodetect')">
                                <FontAwesomeIcon icon="redo" class="mr-1" />{{ "Auto-detect" | l }}
                            </b-button>
                        </div>
                    </b-tab>
                    <b-tab
                        v-if="
                            (!result['conversion_disable'] || !result['datatype_disable']) &&
                            !result['metadata_disable']
                        ">
                        <template v-slot:title>
                            <FontAwesomeIcon icon="database" class="mr-1" />{{ "Datatypes" | l }}
                        </template>
                        <div v-if="!result['datatype_disable']" class="ui-portlet-section">
                            <div class="portlet-header">
                                <div class="portlet-title">
                                    <FontAwesomeIcon icon="database" class="portlet-title-icon fa-fw mr-1" />
                                    <span class="portlet-title-text">
                                        <b itemprop="name">{{ "Assign Datatype" | l }}</b>
                                    </span>
                                </div>
                            </div>
                            <div class="portlet-content">
                                <FormDisplay :inputs="result['datatype_inputs']" @onChange="onDatatype" />
                                <div class="mt-2">
                                    <b-button variant="primary" class="mr-1" @click="submit('datatype', 'datatype')">
                                        <FontAwesomeIcon icon="save" class="mr-1" />{{ "Save" | l }}
                                    </b-button>
                                    <b-button @click="submit('datatype', 'datatype_detect')">
                                        <FontAwesomeIcon icon="redo" class="mr-1" />{{ "Auto-detect" | l }}
                                    </b-button>
                                </div>
                            </div>
                        </div>
                        <div v-if="!result['conversion_disable']" class="ui-portlet-section">
                            <div class="portlet-header">
                                <div class="portlet-title">
                                    <FontAwesomeIcon icon="cog" class="portlet-title-icon fa-fw mr-1" />
                                    <span class="portlet-title-text">
                                        <b itemprop="name">{{ "Convert to Datatype" | l }}</b>
                                    </span>
                                </div>
                            </div>
                            <div class="portlet-content">
                                <FormDisplay :inputs="result['conversion_inputs']" @onChange="onConversion" />
                                <div class="mt-2">
                                    <b-button variant="primary" @click="submit('conversion', 'conversion')">
                                        <FontAwesomeIcon icon="exchange-alt" class="mr-1" />{{ "Create Dataset" | l }}
                                    </b-button>
                                </div>
                            </div>
                        </div>
                    </b-tab>
                    <b-tab v-if="!result['permission_disable']">
                        <template v-slot:title>
                            <FontAwesomeIcon icon="user" class="mr-1" />{{ "Permissions" | l }}
                        </template>
                        <FormDisplay :inputs="result['permission_inputs']" @onChange="onPermission" />
                        <div class="mt-2">
                            <b-button variant="primary" @click="submit('permission', 'permission')">
                                <FontAwesomeIcon icon="save" class="mr-1" />{{ "Save" | l }}
                            </b-button>
                        </div>
                    </b-tab>
                </b-tabs>
            </div>
        </DatasetAttributesProvider>
    </div>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBars, faCog, faDatabase, faExchangeAlt, faRedo, faSave, faUser } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { getGalaxyInstance } from "app";
import FormDisplay from "components/Form/FormDisplay";
import { DatasetAttributesProvider } from "components/providers/DatasetProvider";

import { setAttributes } from "./services";

library.add(faBars, faCog, faDatabase, faExchangeAlt, faRedo, faSave, faUser);

export default {
    components: {
        DatasetAttributesProvider,
        FontAwesomeIcon,
        FormDisplay,
    },
    props: {
        datasetId: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            messageText: null,
            messageVariant: null,
            formData: {},
        };
    },
    computed: {
        hasError() {
            return this.messageVariant === "danger";
        },
    },
    methods: {
        onAttribute(data) {
            this.formData["attribute"] = data;
        },
        onConversion(data) {
            this.formData["conversion"] = data;
        },
        onDatatype(data) {
            this.formData["datatype"] = data;
        },
        onPermission(data) {
            this.formData["permission"] = data;
        },
        onError(messageText) {
            this.messageText = messageText;
            this.messageVariant = "danger";
        },
        submit(key, operation) {
            setAttributes(this.datasetId, this.formData[key], operation).then((response) => {
                this.messageText = response.message;
                this.messageVariant = response.status;
                this._reloadHistory();
            }, this.onError);
        },
        /** reload Galaxy's history after updating dataset's attributes */
        _reloadHistory: function () {
            const Galaxy = getGalaxyInstance();
            if (Galaxy) {
                Galaxy.currHistoryPanel.loadCurrentHistory();
            }
        },
    },
};
</script>
