<script setup>
import Vue, { defineComponent } from "vue";
import { reactive, computed } from "vue";
import BootstrapVue from "bootstrap-vue";
import axios from "axios";
import { prependPath } from "utils/redirect";
import { errorMessageAsString } from "utils/simple-error";
import DatabaseEditTab from "./DatabaseEditTab";
import SuitableConvertersTab from "./SuitableConvertersTab";
import ChangeDatatypeTab from "./ChangeDatatypeTab";
import { DbKeyProvider, SuitableConvertersProvider } from "../../providers";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faDatabase, faTable, faBars, faUser, faCog } from "@fortawesome/free-solid-svg-icons";
import { useConfig } from "composables/useConfig";

library.add(faDatabase, faTable, faBars, faUser, faCog);

const { config } = useConfig();

Vue.use(BootstrapVue);
const components = defineComponent({
    DatabaseEditTab,
    SuitableConvertersTab,
    ChangeDatatypeTab,
    FontAwesomeIcon,
    DbKeyProvider,
    SuitableConvertersProvider,
});
const props = defineProps({
    collection_id: {
        type: String,
        required: true,
    },
});

const data = reactive({
    attributes_data: {},
    errorMessage: null,
    jobError: null,
    noQuotaIncrease: true,
});

const databaseKeyFromElements = computed(() => {
    return data.attributes_data.dbkey;
});

const newCollectionInfoMessage = computed(() => {
    let newCollectionMessage = "This will create a new collection in your History.";
    if (data.noQuotaIncrease) {
        newCollectionMessage += " Your quota usage will not increase.";
    }
    return newCollectionMessage;
});

function created() {
    this.getCollectionDataAndAttributes();
}

async function getCollectionDataAndAttributes() {
    let attributesGet = this.$store.getters.getCollectionAttributes(this.collection_id);
    if (attributesGet == null) {
        await this.$store.dispatch("fetchCollectionAttributes", this.collection_id);
        attributesGet = this.$store.getters.getCollectionAttributes(this.collection_id);
    }
    data.attributes_data = attributesGet;
}
function clickedSave(attribute, newValue) {
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
}
function clickedConvert(selectedConverter) {
    const url = prependPath(`/api/tools/${selectedConverter.tool_id}/convert`);
    const data = {
        src: "hdca",
        id: this.collection_id,
        source_type: selectedConverter.original_type,
        target_type: selectedConverter.target_type,
    };
    axios.post(url, data).catch(this.handleError);
}
function handleError(err) {
    data.errorMessage = errorMessageAsString(err, "History import failed.");
    if (err?.data?.stderr) {
        data.jobError = err.data;
    }
}
</script>

<template>
    <div>
        <h4>{{ l("Edit Collection Attributes") }}</h4>
        <b-alert show variant="info" dismissible>
            {{ l(newCollectionInfoMessage) }}
        </b-alert>
        <div v-if="data.jobError">
            <b-alert show variant="danger" dismissible>
                {{ data.errorMessage }}
            </b-alert>
        </div>
        <b-tabs content-class="mt-3">
            <b-tab @click="data.noQuotaIncrease = true">
                <template v-slot:title> <font-awesome-icon icon="table" /> &nbsp; {{ l("Database/Build") }} </template>
                In template
                <DbKeyProvider v-slot="{ item, loading }">
                    In provider
                    <div v-if="loading">
                        <b-spinner label="Loading Database/Builds..."></b-spinner>
                    </div>
                    <div v-else>
                        In edit
                        <database-edit-tab
                            v-if="item && databaseKeyFromElements"
                            :database-key-from-elements="databaseKeyFromElements"
                            :genomes="item"
                            @clicked-save="clickedSave" />
                    </div>
                </DbKeyProvider>
            </b-tab>
            <SuitableConvertersProvider :id="collection_id" v-slot="{ item }">
                <b-tab v-if="item && item.length" @click="data.noQuotaIncrease = false">
                    <template v-slot:title> <font-awesome-icon icon="cog" /> &nbsp; {{ l("Convert") }} </template>
                    <suitable-converters-tab :suitable-converters="item" @clicked-convert="clickedConvert" />
                </b-tab>
            </SuitableConvertersProvider>
            <b-tab v-if="config.enable_celery_tasks">
                <template v-slot:title> <font-awesome-icon icon="database" /> &nbsp; {{ l("Datatypes") }} </template>
                <change-datatype-tab />
            </b-tab>
        </b-tabs>
    </div>
</template>
