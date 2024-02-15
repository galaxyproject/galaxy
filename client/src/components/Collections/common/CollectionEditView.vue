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
            <b-tab
                title-link-class="collection-edit-change-genome-nav"
                @click="updateInfoMessage(newCollectionMessage + ' ' + noQuotaIncreaseMessage)">
                <template v-slot:title> <FontAwesomeIcon icon="table" /> &nbsp; {{ l("Database/Build") }}</template>
                <DbKeyProvider v-slot="{ item, loading }">
                    <div v-if="loading"><b-spinner label="Loading Database/Builds..."></b-spinner></div>
                    <div v-else>
                        <DatabaseEditTab
                            v-if="item && databaseKeyFromElements"
                            :database-key-from-elements="databaseKeyFromElements"
                            :genomes="item"
                            @clicked-save="clickedSave" />
                    </div>
                </DbKeyProvider>
            </b-tab>
            <SuitableConvertersProvider :id="collectionId" v-slot="{ item }">
                <b-tab
                    v-if="item && item.length"
                    title-link-class="collection-edit-convert-datatype-nav"
                    @click="updateInfoMessage(newCollectionMessage)">
                    <template v-slot:title> <FontAwesomeIcon icon="cog" /> &nbsp; {{ l("Convert") }}</template>
                    <SuitableConvertersTab :suitable-converters="item" @clicked-convert="clickedConvert" />
                </b-tab>
            </SuitableConvertersProvider>
            <b-tab
                v-if="isConfigLoaded && config.enable_celery_tasks"
                title-link-class="collection-edit-change-datatype-nav"
                @click="updateInfoMessage(expectWaitTimeMessage)">
                <template v-slot:title> <FontAwesomeIcon icon="database" /> &nbsp; {{ l("Datatypes") }} </template>
                <DatatypesProvider v-slot="{ item, loading }">
                    <div v-if="loading"><LoadingSpan :message="loadingString" /></div>
                    <div v-else>
                        <ChangeDatatypeTab
                            v-if="item && datatypeFromElements"
                            :datatype-from-elements="datatypeFromElements"
                            :datatypes="item"
                            @clicked-save="clickedDatatypeChange" />
                    </div>
                </DatatypesProvider>
            </b-tab>
        </b-tabs>
    </div>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBars, faCog, faDatabase, faTable, faUser } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
import BootstrapVue from "bootstrap-vue";
import { mapState } from "pinia";
import { prependPath } from "utils/redirect";
import { errorMessageAsString } from "utils/simple-error";
import Vue from "vue";

import { useConfig } from "@/composables/config";
import { useCollectionAttributesStore } from "@/stores/collectionAttributesStore";
import { useHistoryStore } from "@/stores/historyStore";

import { DatatypesProvider, DbKeyProvider, SuitableConvertersProvider } from "../../providers";
import ChangeDatatypeTab from "./ChangeDatatypeTab";
import DatabaseEditTab from "./DatabaseEditTab";
import SuitableConvertersTab from "./SuitableConvertersTab";

import LoadingSpan from "@/components/LoadingSpan.vue";

library.add(faDatabase, faTable, faBars, faUser, faCog);

Vue.use(BootstrapVue);
export default {
    components: {
        DatabaseEditTab,
        SuitableConvertersTab,
        FontAwesomeIcon,
        DbKeyProvider,
        SuitableConvertersProvider,
        ChangeDatatypeTab,
        DatatypesProvider,
        LoadingSpan,
    },
    props: {
        collectionId: {
            type: String,
            required: true,
        },
    },
    setup() {
        const { config, isConfigLoaded } = useConfig(true);
        return { config, isConfigLoaded };
    },
    data: function () {
        return {
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
        ...mapState(useHistoryStore, ["currentHistoryId"]),
        ...mapState(useCollectionAttributesStore, ["getAttributes"]),
        attributesData() {
            return this.getAttributes(this.collectionId);
        },
        databaseKeyFromElements: function () {
            return this.attributesData?.dbkey;
        },
        datatypeFromElements: function () {
            return this.attributesData?.extension;
        },
    },
    methods: {
        updateInfoMessage: function (strMessage) {
            this.infoMessage = strMessage;
        },
        clickedSave: function (attribute, newValue) {
            const url = prependPath(`/api/dataset_collections/${this.collectionId}/copy`);
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
                id: this.collectionId,
                source_type: selectedConverter.original_type,
                target_type: selectedConverter.target_type,
            };
            axios.post(url, data).catch(this.handleError);
        },
        clickedDatatypeChange: function (selectedDatatype) {
            const url = prependPath(`/api/histories/${this.currentHistoryId}/contents/bulk`);
            const data = {
                operation: "change_datatype",
                items: [
                    {
                        history_content_type: "dataset_collection",
                        id: this.collectionId,
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
