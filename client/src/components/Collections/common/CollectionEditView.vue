<template>
    <div aria-labelledby="collection-edit-view-heading">
        <h1 id="collection-edit-view-heading" class="h-lg">{{ l("Edit Collection Attributes") }}</h1>
        <b-alert show variant="info" dismissible>
            {{ l(infoMessage) }}
        </b-alert>
        <div v-if="jobError">
            <b-alert show variant="danger" dismissible>
                {{ l(errorMessage) }}
            </b-alert>
        </div>
        <b-tabs content-class="mt-3">
            <b-tab @click="updateInfoMessage(newCollectionMessage + ' ' + noQuotaIncreaseMessage)">
                <template v-slot:title> <font-awesome-icon icon="table" /> &nbsp; {{ l("Database/Build") }}</template>
                <db-key-provider v-slot="{ item, loading }">
                    <div v-if="loading"><b-spinner label="Loading Database/Builds..."></b-spinner></div>
                    <div v-else>
                        <database-edit-tab
                            v-if="item && databaseKeyFromElements"
                            :database-key-from-elements="databaseKeyFromElements"
                            :genomes="item"
                            @clicked-save="clickedSave" />
                    </div>
                </db-key-provider>
            </b-tab>
            <SuitableConvertersProvider :id="collection_id" v-slot="{ item }">
                <b-tab v-if="item && item.length" @click="updateInfoMessage(newCollectionMessage)">
                    <template v-slot:title> <font-awesome-icon icon="cog" /> &nbsp; {{ l("Convert") }}</template>
                    <suitable-converters-tab :suitable-converters="item" @clicked-convert="clickedConvert" />
                </b-tab>
            </SuitableConvertersProvider>
            <ConfigProvider v-slot="{ config }">
                <b-tab v-if="config.enable_celery_tasks" @click="updateInfoMessage(expectWaitTimeMessage)">
                    <template v-slot:title>
                        <font-awesome-icon icon="database" /> &nbsp; {{ l("Datatypes") }}
                    </template>
                    <datatypes-provider v-slot="{ item, loading }">
                        <div v-if="loading"><loading-span :message="loadingString" /></div>
                        <div v-else>
                            <change-datatype-tab
                                v-if="item && datatypeFromElements"
                                :datatype-from-elements="datatypeFromElements"
                                :datatypes="item"
                                @clicked-save="clickedDatatypeChange" />
                        </div>
                    </datatypes-provider>
                </b-tab>
            </ConfigProvider>
        </b-tabs>
    </div>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import axios from "axios";
import { prependPath } from "utils/redirect";
import { errorMessageAsString } from "utils/simple-error";
import DatabaseEditTab from "./DatabaseEditTab";
import SuitableConvertersTab from "./SuitableConvertersTab";
import { DbKeyProvider, SuitableConvertersProvider, DatatypesProvider } from "../../providers";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faDatabase, faTable, faBars, faUser, faCog } from "@fortawesome/free-solid-svg-icons";
import ConfigProvider from "components/providers/ConfigProvider";
import ChangeDatatypeTab from "./ChangeDatatypeTab";
import LoadingSpan from "../../LoadingSpan.vue";

library.add(faDatabase, faTable, faBars, faUser, faCog);

Vue.use(BootstrapVue);
export default {
    components: {
        DatabaseEditTab,
        SuitableConvertersTab,
        FontAwesomeIcon,
        DbKeyProvider,
        SuitableConvertersProvider,
        ConfigProvider,
        ChangeDatatypeTab,
        DatatypesProvider,
        LoadingSpan,
    },
    props: {
        collection_id: {
            type: String,
            required: true,
        },
    },
    data: function () {
        return {
            attributesData: {},
            errorMessage: null,
            jobError: null,
            noQuotaIncrease: true,
            loadingString: "Loading Datatypes",
            infoMessage: "This will create a new collection in your History. Your quota will not increase.", //initialmessage on first/database tab
            newCollectionMessage: "This will create a new collection in your History.",
            noQuotaIncreaseMessage: "Your quota will not increase.",
            expectWaitTimeMessage: "This operation might take a short while, depending on the size of your collection.",
        };
    },
    computed: {
        databaseKeyFromElements: function () {
            return this.attributesData.dbkey;
        },
        datatypeFromElements: function () {
            return this.attributesData.extension;
        },
        historyId: function () {
            return this.$store.getters["history/currentHistoryId"];
        },
    },
    created() {
        this.getCollectionDataAndAttributes();
    },
    methods: {
        updateInfoMessage: function (strMessage) {
            this.infoMessage = strMessage;
        },
        getCollectionDataAndAttributes: async function () {
            let attributesGet = this.$store.getters.getCollectionAttributes(this.collection_id);
            if (attributesGet == null) {
                await this.$store.dispatch("fetchCollectionAttributes", this.collection_id);
                attributesGet = this.$store.getters.getCollectionAttributes(this.collection_id);
            }
            this.attributesData = attributesGet;
        },
        clickedSave: function (attribute, newValue) {
            const url = prependPath(`/api/dataset_collections/${this.collection_id}/copy`);
            const data = {};
            if (attribute == "dbkey") {
                data["dbkey"] = newValue.id;
            } else {
                // TODO: extend this to other attributes that could be changed
                console.error(`Changing ${attribute} not implemented`);
                return;
            }
            axios.post(url, data).catch(this.handleError);
        },
        clickedConvert: function (selectedConverter) {
            const url = prependPath(`/api/tools/${selectedConverter.tool_id}/convert`);
            const data = {
                src: "hdca",
                id: this.collection_id,
                source_type: selectedConverter.original_type,
                target_type: selectedConverter.target_type,
            };
            axios.post(url, data).catch(this.handleError);
        },
        clickedDatatypeChange: function (selectedDatatype) {
            const url = prependPath(`/api/histories/${this.historyId}/contents/bulk`);
            const data = {
                operation: "change_datatype",
                items: [
                    {
                        history_content_type: "dataset_collection",
                        id: this.collection_id,
                    },
                ],
                params: {
                    type: "change_datatype",
                    datatype: selectedDatatype.id,
                },
            };
            axios.put(url, data).catch(this.handleError);
        },
        handleError: function (err) {
            this.errorMessage = errorMessageAsString(err, "History import failed.");
            if (err?.data?.stderr) {
                this.jobError = err.data;
            }
        },
    },
};
</script>
