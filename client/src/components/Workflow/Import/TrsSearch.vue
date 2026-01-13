<script setup lang="ts">
import { faQuestion, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
import { BAlert, BFormInput, BInputGroup, BInputGroupAppend, BTable } from "bootstrap-vue";
import { computed, type Ref, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { getRedirectOnImportPath } from "@/components/Workflow/redirectPath";
import { Services } from "@/components/Workflow/services";
import { useMarkdown } from "@/composables/markdown";
import { withPrefix } from "@/utils/redirect";

import type { TrsSelection } from "./types";

import GButton from "@/components/BaseComponents/GButton.vue";
import GCard from "@/components/Common/GCard.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import TrsServerSelection from "@/components/Workflow/Import/TrsServerSelection.vue";
import TrsTool from "@/components/Workflow/Import/TrsTool.vue";

interface Props {
    mode?: "modal" | "wizard";
}

const props = withDefaults(defineProps<Props>(), {
    mode: "modal",
});

const emit = defineEmits<{
    (e: "input-valid", valid: boolean): void;
}>();

type TrsSearchData = {
    id: string;
    name: string;
    description: string;
    [key: string]: unknown;
};

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

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
const selectedTool = ref<TrsSearchData | null>(null);
const selectedVersion = ref<string | undefined>(undefined);

const hasErrorMessage = computed(() => {
    return errorMessage.value != null;
});

// Validation state for wizard mode
const isValid = computed(() => {
    return selectedTool.value !== null && selectedVersion.value !== undefined;
});

watch(isValid, (newValue) => {
    emit("input-valid", newValue);
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
        // Reset selection state when search is cleared
        selectedTool.value = null;
        selectedVersion.value = undefined;
    } else {
        loading.value = true;

        try {
            const response = await axios.get(
                withPrefix(`/api/trs_search?query=${query.value}&trs_server=${trsServer.value}`),
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

function showRowDetails(row: any, _index: number, e: MouseEvent) {
    if ((e.target as Node | undefined)?.nodeName !== "A") {
        // Collapse all other rows
        itemsComputed.value.forEach((item) => {
            if (item !== row) {
                item._showDetails = false;
            }
        });
        // Toggle the clicked row
        const wasExpanded = row._showDetails;
        row._showDetails = !row._showDetails;

        // If collapsing the row, reset selection state
        if (wasExpanded) {
            selectedTool.value = null;
            selectedVersion.value = undefined;
        }
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

function onVersionSelected(toolData: TrsSearchData, versionId: string) {
    selectedTool.value = toolData;
    selectedVersion.value = versionId;

    // Only auto-import in modal mode
    if (props.mode === "modal") {
        importVersion(trsSelection.value?.id, toolData.id, versionId);
    }
}

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

// Expose method for wizard submit
function triggerImport() {
    if (selectedTool.value && selectedVersion.value) {
        importVersion(trsSelection.value?.id, selectedTool.value.id, selectedVersion.value);
    }
}

defineExpose({ triggerImport });
</script>

<template>
    <GCard class="workflow-import-trs-search" title="GA4GH Tool Registry Server (TRS) Workflow Search">
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
                    <GButton tooltip size="small" data-description="show help toggle" :title="searchHelp">
                        <FontAwesomeIcon :icon="faQuestion" />
                    </GButton>

                    <GButton size="small" title="clear search" @click="query = ''">
                        <FontAwesomeIcon :icon="faTimes" />
                    </GButton>
                </BInputGroupAppend>
            </BInputGroup>
        </div>

        <div class="vertical-scroll">
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
                caption-top
                :busy="loading"
                tbody-tr-class="clickable-row"
                @row-clicked="showRowDetails">
                <template v-slot:row-details="row">
                    <BCard>
                        <BAlert v-if="importing" variant="info" show>
                            <LoadingSpan message="Importing workflow" />
                        </BAlert>

                        <TrsTool
                            :trs-tool="row.item.data"
                            :mode="props.mode"
                            @onImport="(versionId) => onVersionSelected(row.item.data, versionId)"
                            @onSelect="(versionId) => onVersionSelected(row.item.data, versionId)" />
                    </BCard>
                </template>

                <template v-slot:cell(description)="row">
                    <span class="trs-description" v-html="renderMarkdown(row.item.data.description)" />
                </template>
            </BTable>
        </div>
    </GCard>
</template>

<style>
.trs-description {
    position: relative;
    overflow: hidden;
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 3;
    line-clamp: 3;
}
.vertical-scroll {
    max-height: 600px;
    overflow-y: auto;
}
.clickable-row:not(.b-table-details) {
    cursor: pointer;
}
.clickable-row:not(:first-child) {
    border-top: 1px double #ccc;
}
.clickable-row.b-table-has-details {
    border: 2px solid var(--brand-primary, #007bff);
    border-bottom: none;
}
.clickable-row.b-table-details {
    border: 2px solid var(--brand-primary, #007bff);
    border-top: none;
}
.clickable-row.b-table-details:hover {
    background: unset;
}
</style>
