<script setup lang="ts">
import axios from "axios";
import TrsTool from "./TrsTool.vue";
import { Services } from "../services";
import { withPrefix } from "@/utils/redirect";
import { computed, ref, watch, type Ref } from "vue";
import { getRedirectOnImportPath } from "../redirectPath";
import LoadingSpan from "@/components/LoadingSpan.vue";
import TrsServerSelection from "./TrsServerSelection.vue";
import { useRouter } from "vue-router/composables";
import { BCard } from "bootstrap-vue";
import type { TrsSelection } from "./types";

type TrsSearchData = {
    id: string;
    name: string;
    description: string;
    [key: string]: unknown;
};

const fields = [
    { key: "name", label: "Name" },
    { key: "description", label: "Description" },
    { key: "organization", label: "Organization" },
];

const query = ref("");
const results: Ref<TrsSearchData[]> = ref([]);
const trsServer = ref("");
const loading = ref(false);
const importing = ref(false);
const trsSelection: Ref<TrsSelection | null> = ref(null);
const errorMessage: Ref<string | null> = ref(null);

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

watch(query, async () => {
    if (query.value == "") {
        results.value = [];
    } else {
        loading.value = true;

        try {
            const response = await axios.get(
                withPrefix(`/api/trs_search?query=${query.value}&trs_server=${trsServer.value}`)
            );
            results.value = response.data;
        } catch (e) {
            errorMessage.value = e as string;
        }

        loading.value = false;
    }
});

function onTrsSelection(selection: TrsSelection) {
    trsSelection.value = selection;
    trsServer.value = selection.id;
    query.value = "";
}

function onTrsSelectionError(message: string) {
    errorMessage.value = message;
}

function showRowDetails(row: BCard, index: number, e: MouseEvent) {
    if ((e.target as Node | undefined)?.nodeName !== "A") {
        row._showDetails = !row._showDetails;
    }
}

function computeItems(items: TrsSearchData[]) {
    return items.map((item) => {
        return {
            id: item.id,
            name: item.name,
            description: item.description,
            data: item,
            _showDetails: false,
        };
    });
}

const router = useRouter();

async function importVersion(trsId?: string, toolIdToImport?: string, version?: string, isRunFormRedirect = false) {
    if (!trsId || !toolIdToImport) {
        errorMessage.value = "Import Failed. Unknown Id";
        return;
    }

    importing.value = true;
    errorMessage.value = null;

    try {
        const response = await services.importTrsTool(trsId, toolIdToImport, version);
        const path = getRedirectOnImportPath(response, isRunFormRedirect);

        router.push(path);
    } catch (e) {
        errorMessage.value = (e as string) || "Import failed for an unknown reason.";
    }

    importing.value = false;
}
</script>

<template>
    <b-card title="GA4GH Tool Registry Server (TRS) Workflow Search">
        <b-alert :show="hasErrorMessage" variant="danger">{{ errorMessage }}</b-alert>

        <div class="mb-3">
            <b>TRS Server:</b>
            <TrsServerSelection
                :trs-selection="trsSelection"
                @onTrsSelection="onTrsSelection"
                @onError="onTrsSelectionError" />
        </div>

        <div>
            <b-input-group class="mb-3">
                <b-form-input
                    id="trs-search-query"
                    v-model="query"
                    debounce="500"
                    placeholder="search query"
                    data-description="filter text input"
                    @keyup.esc="query = ''" />
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
                            @onImport="(versionId) => importVersion(trsSelection?.id, row.item.data.id, versionId)" />
                    </b-card>
                </template>
            </b-table>
        </div>
    </b-card>
</template>
