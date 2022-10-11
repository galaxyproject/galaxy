<script setup>
import axios from "axios";
import TrsTool from "./TrsTool";
import { Services } from "../services";
import { safePath } from "utils/redirect";
import { computed, ref, watch } from "vue";
import { redirectOnImport } from "../utils";
import LoadingSpan from "components/LoadingSpan";
import TrsServerSelection from "./TrsServerSelection";
import DebouncedInput from "components/DebouncedInput";

const fields = [
    { key: "name", label: "Name" },
    { key: "description", label: "Description" },
    { key: "organization", label: "Organization" },
];

const query = ref("");
const results = ref([]);
const trsServer = ref("");
const loading = ref(false);
const importing = ref(false);
const trsSelection = ref(null);
const errorMessage = ref(null);

const hasErrorMessage = computed(() => {
    return errorMessage.value != null;
});
const itemsComputed = computed(() => {
    return computeItems(results.value);
});
const searchHelp = computed(() => {
    return "Search by workflow description. Tags (key:value) can be used to also search by metadata - for instance name:example. Available tags include organization and name.";
});

const services = new Services();

watch(query, () => {
    if (query.value == "") {
        results.value = [];
    } else {
        loading.value = true;
        axios
            .get(safePath(`/api/trs_search?query=${query.value}&trs_server=${trsServer.value}`))
            .then((response) => {
                results.value = response.data;
            })
            .catch((e) => {
                errorMessage.value = e;
            })
            .finally(() => {
                loading.value = false;
            });
    }
});

const onTrsSelection = (selection) => {
    trsSelection.value = selection;
    trsServer.value = selection.id;
    query.value = "";
};

const onTrsSelectionError = (message) => {
    errorMessage.value = message;
};
const showRowDetails = (row, index, e) => {
    if (e.target.nodeName != "A") {
        row._showDetails = !row._showDetails;
    }
};

const computeItems = (items) => {
    return items.map((item) => {
        return {
            id: item.id,
            name: item.name,
            description: item.description,
            data: item,
            _showDetails: false,
        };
    });
};

const importVersion = (trsId, toolIdToImport, version = null, isRunFormRedirect = false) => {
    importing.value = true;
    errorMessage.value = null;
    services
        .importTrsTool(trsId, toolIdToImport, version)
        .then((response) => {
            redirectOnImport(safePath("/"), response, isRunFormRedirect);
        })
        .catch((e) => {
            errorMessage.value = e || "Import failed for an unknown reason.";
        })
        .finally(() => {
            importing.value = false;
        });
};
</script>

<template>
    <b-card title="GA4GH Tool Registry Server (TRS) Workflow Search">
        <b-alert :show="hasErrorMessage" variant="danger">{{ errorMessage }}</b-alert>

        <div class="mb-3">
            <b>TRS Server:</b>
            <TrsServerSelection @onTrsSelection="onTrsSelection" @onError="onTrsSelectionError" />
        </div>

        <div>
            <b-input-group class="mb-3">
                <DebouncedInput v-slot="{ value, input }" v-model="query">
                    <b-form-input
                        :value="value"
                        placeholder="search query"
                        data-description="filter text input"
                        @input="input"
                        @keyup.esc="query = ''" />
                </DebouncedInput>
                <b-input-group-append>
                    <b-button
                        v-b-tooltip
                        placement="bottom"
                        size="sm"
                        data-description="show help toggle"
                        :title="searchHelp">
                        <icon icon="question" />
                    </b-button>
                    <b-button size="sm" data-description="show deleted filter toggle" @click="query = ''">
                        <icon icon="times" />
                    </b-button>
                </b-input-group-append>
            </b-input-group>
        </div>
        <div>
            <b-alert v-if="loading" variant="info" show>
                <LoadingSpan :message="`Searching for ${query}, this may take a while - please be patient`" />
            </b-alert>
            <b-alert v-else-if="!query" variant="info" show> Enter search query to begin search. </b-alert>
            <b-alert v-else-if="results.length == 0" variant="info" show>
                No search results found, refine your search.
            </b-alert>
            <b-table
                v-else
                :fields="fields"
                :items="itemsComputed"
                hover
                striped
                caption-top
                :busy="loading"
                @row-clicked="showRowDetails">
                <template v-slot:row-details="row">
                    <b-card>
                        <b-alert v-if="importing" variant="info" show>
                            <LoadingSpan message="Importing workflow" />
                        </b-alert>
                        <TrsTool
                            :trs-tool="row.item.data"
                            @onImport="importVersion(trsSelection.id, row.item.data.id, $event)" />
                    </b-card>
                </template>
            </b-table>
        </div>
    </b-card>
</template>
