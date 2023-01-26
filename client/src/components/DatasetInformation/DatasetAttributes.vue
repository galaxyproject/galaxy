<template>
    <div aria-labelledby="dataset-attributes-heading">
        <h1 id="dataset-attributes-heading" v-localize class="h-lg">Edit Dataset Attributes</h1>
        <b-alert v-if="messageText" :variant="messageVariant" show>
            {{ messageText | l }}
        </b-alert>
        <DatasetAttributesProvider :id="datasetId" v-slot="{ result, loading }" @error="onError">
            <div v-if="!loading" class="mt-3">
                <b-tabs>
                    <b-tab v-if="!result['attribute_disable']">
                        <template v-slot:title>
                            <font-awesome-icon icon="bars" class="mr-1" />{{ "Attributes" | l }}
                        </template>
                        <FormDisplay :inputs="result['attribute_inputs']" @onChange="onAttribute" />
                        <div class="mt-2">
                            <b-button
                                id="dataset-attributes-default-save"
                                variant="primary"
                                class="mr-1"
                                @click="submit('attribute', 'attributes')">
                                <font-awesome-icon icon="save" class="mr-1" />{{ "Save" | l }}
                            </b-button>
                            <b-button v-if="!result['metadata_disable']" @click="submit('attribute', 'autodetect')">
                                <font-awesome-icon icon="redo" class="mr-1" />{{ "Auto-detect" | l }}
                            </b-button>
                        </div>
                    </b-tab>
                    <b-tab
                        v-if="
                            (!result['conversion_disable'] || !result['datatype_disable']) &&
                            !result['metadata_disable']
                        ">
                        <template v-slot:title>
                            <span v-if="!result['conversion_disable']">
                                <font-awesome-icon icon="cog" class="mr-1" />{{ "Convert" | l }}
                            </span>
                            <span v-else>
                                <font-awesome-icon icon="database" class="mr-1" />{{ "Datatypes" | l }}
                            </span>
                        </template>
                        <div v-if="!result['conversion_disable']" class="ui-portlet-section">
                            <div class="portlet-header">
                                <div class="portlet-title">
                                    <font-awesome-icon icon="cog" class="portlet-title-icon fa-fw mr-1" />
                                    <span class="portlet-title-text">
                                        <b itemprop="name">{{ "Convert" | l }}</b>
                                    </span>
                                </div>
                            </div>
                            <div class="portlet-content">
                                <FormDisplay :inputs="result['conversion_inputs']" @onChange="onConversion" />
                                <div class="mt-2">
                                    <b-button variant="primary" @click="submit('conversion', 'conversion')">
                                        <font-awesome-icon icon="exchange-alt" class="mr-1" />{{ "Create Dataset" | l }}
                                    </b-button>
                                </div>
                            </div>
                        </div>
                        <div v-if="!result['datatype_disable']" class="ui-portlet-section">
                            <div class="portlet-header">
                                <div class="portlet-title">
                                    <font-awesome-icon icon="database" class="portlet-title-icon fa-fw mr-1" />
                                    <span class="portlet-title-text">
                                        <b itemprop="name">{{ "Datatypes" | l }}</b>
                                    </span>
                                </div>
                            </div>
                            <div class="portlet-content">
                                <FormDisplay :inputs="result['datatype_inputs']" @onChange="onDatatype" />
                                <div class="mt-2">
                                    <b-button variant="primary" class="mr-1" @click="submit('datatype', 'datatype')">
                                        <font-awesome-icon icon="save" class="mr-1" />{{ "Save" | l }}
                                    </b-button>
                                    <b-button @click="submit('datatype', 'datatype_detect')">
                                        <font-awesome-icon icon="redo" class="mr-1" />{{ "Auto-detect" | l }}
                                    </b-button>
                                </div>
                            </div>
                        </div>
                    </b-tab>
                    <b-tab v-if="!result['permission_disable']">
                        <template v-slot:title>
                            <font-awesome-icon icon="user" class="mr-1" />{{ "Permissions" | l }}
                        </template>
                        <FormDisplay :inputs="result['permission_inputs']" @onChange="onPermission" />
                        <div class="mt-2">
                            <b-button variant="primary" @click="submit('permission', 'permission')">
                                <font-awesome-icon icon="save" class="mr-1" />{{ "Save" | l }}
                            </b-button>
                        </div>
                    </b-tab>
                </b-tabs>
            </div>
        </DatasetAttributesProvider>
    </div>
</template>

<script>
import { getGalaxyInstance } from "app";
import FormDisplay from "components/Form/FormDisplay";
import { DatasetAttributesProvider } from "components/providers/DatasetProvider";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBars, faCog, faDatabase, faExchangeAlt, faRedo, faSave, faUser } from "@fortawesome/free-solid-svg-icons";
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
