<template>
    <div>
        <h4>{{ l("Edit Collection Attributes") }}</h4>
        <b-alert show variant="info" dismissible>
            {{ l(newCollectionInfoMessage) }}
        </b-alert>
        <div v-if="jobError">
            <b-alert show variant="danger" dismissible>
                {{ errorMessage }}
            </b-alert>
        </div>
        <b-tabs content-class="mt-3">
            <b-tab @click="noQuotaIncrease = true">
                <template v-slot:title> <font-awesome-icon icon="table" /> &nbsp; {{ l("Database/Build") }}</template>
                <GenomeProvider v-slot="{ item, loading }">
                    <div v-if="loading"><b-spinner label="Loading Genomes..."></b-spinner></div>
                    <div v-else>
                        <database-edit-tab
                            v-if="item && databaseKeyFromElements"
                            :database-key-from-elements="databaseKeyFromElements"
                            :genomes="item"
                            @clicked-save="clickedSave" />
                    </div>
                </GenomeProvider>
            </b-tab>
            <SuitableConvertersProvider :id="collection_id" v-slot="{ item }">
                <b-tab v-if="item && item.length" @click="noQuotaIncrease = false">
                    <template v-slot:title> <font-awesome-icon icon="cog" /> &nbsp; {{ l("Convert") }}</template>
                    <suitable-converters-tab :suitable-converters="item" @clicked-convert="clickedConvert" />
                </b-tab>
            </SuitableConvertersProvider>
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
import { GenomeProvider, SuitableConvertersProvider } from "../../providers";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faDatabase, faTable, faBars, faUser, faCog } from "@fortawesome/free-solid-svg-icons";

library.add(faDatabase, faTable, faBars, faUser, faCog);

Vue.use(BootstrapVue);
export default {
    components: {
        DatabaseEditTab,
        SuitableConvertersTab,
        FontAwesomeIcon,
        GenomeProvider,
        SuitableConvertersProvider,
    },
    props: {
        collection_id: {
            type: String,
            required: true,
        },
    },
    data: function () {
        return {
            attributes_data: {},
            errorMessage: null,
            jobError: null,
            noQuotaIncrease: true,
        };
    },
    computed: {
        databaseKeyFromElements: function () {
            return this.attributes_data.dbkey;
        },
        newCollectionInfoMessage: function () {
            let newCollectionMessage = "This will create a new collection in your History.";
            if (this.noQuotaIncrease) {
                newCollectionMessage += " Your quota usage will not increase.";
            }
            return newCollectionMessage;
        },
    },
    created() {
        this.getCollectionDataAndAttributes();
    },
    methods: {
        getCollectionDataAndAttributes: async function () {
            let attributesGet = this.$store.getters.getCollectionAttributes(this.collection_id);
            if (attributesGet == null) {
                await this.$store.dispatch("fetchCollectionAttributes", this.collection_id);
                attributesGet = this.$store.getters.getCollectionAttributes(this.collection_id);
            }
            this.attributes_data = attributesGet;
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
        handleError: function (err) {
            this.errorMessage = errorMessageAsString(err, "History import failed.");
            if (err?.data?.stderr) {
                this.jobError = err.data;
            }
        },
    },
};
</script>
