<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faQuestion, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
import { BAlert, BButton, BCard, BFormInput, BInputGroup, BInputGroupAppend, BTable } from "bootstrap-vue";
import { computed, type Ref, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { getRedirectOnImportPath } from "@/components/Workflow/redirectPath";
import { Services } from "@/components/Workflow/services";
import { withPrefix } from "@/utils/redirect";

import type { TrsSelection } from "./types";

import LoadingSpan from "@/components/LoadingSpan.vue";
import TrsServerSelection from "@/components/Workflow/Import/TrsServerSelection.vue";
import TrsTool from "@/components/Workflow/Import/TrsTool.vue";

library.add(faQuestion, faTimes);

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
    <BCard class="workflow-import-trs-search" title="GA4GH Tool Registry Server (TRS) Workflow Search">
        <BAlert :show="hasErrorMessage" variant="danger">
            {{ errorMessage }}
        </BAlert>

        <div class="mb-3">
            <b>TRS Server:</b>

            <TrsServerSelection
                :trs-selection="trsSelection"
                @onTrsSelection="onTrsSelection"
                @onError="onTrsSelectionError" />
        </div>

        <div>
            <BInputGroup class="mb-3">
                <BFormInput
                    id="trs-search-query"
                    v-model="query"
                    debounce="500"
                    placeholder="search query"
                    data-description="filter text input"
                    @keyup.esc="query = ''" />

                <BInputGroupAppend>
                    <BButton
                        v-b-tooltip
                        placement="bottom"
                        size="sm"
                        data-description="show help toggle"
                        :title="searchHelp">
                        <FontAwesomeIcon :icon="faQuestion" />
                    </BButton>

                    <BButton size="sm" title="clear search" @click="query = ''">
                        <FontAwesomeIcon :icon="faTimes" />
                    </BButton>
                </BInputGroupAppend>
            </BInputGroup>
        </div>

        <div>
            <BAlert v-if="loading" variant="info" show>
                <LoadingSpan :message="`Searching for ${query}, this may take a while - please be patient`" />
            </BAlert>
            <BAlert v-else-if="!query" variant="info" show> Enter search query to begin search. </BAlert>
            <BAlert v-else-if="results.length == 0" variant="info" show>
                No search results found, refine your search.
            </BAlert>
            <BTable
                v-else
                :fields="fields"
                :items="itemsComputed"
                hover
                striped
                caption-top
                :busy="loading"
                @row-clicked="showRowDetails">
                <template v-slot:row-details="row">
                    <BCard>
                        <BAlert v-if="importing" variant="info" show>
                            <LoadingSpan message="Importing workflow" />
                        </BAlert>

                        <TrsTool
                            :trs-tool="row.item.data"
                            @onImport="(versionId) => importVersion(trsSelection?.id, row.item.data.id, versionId)" />
                    </BCard>
                </template>
            </BTable>
        </div>
    </BCard>
</template>
