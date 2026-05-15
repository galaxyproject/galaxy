<script setup lang="ts">
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
import { BAlert, BCard, BFormInput, BInputGroup, BInputGroupAppend } from "bootstrap-vue";
import { computed, type Ref, ref, watch } from "vue";
import { useRouter } from "vue-router";

import type { RowClickEvent, TableField } from "@/components/Common/GTable.types";
import { getRedirectOnImportPath } from "@/components/Workflow/redirectPath";
import { Services } from "@/components/Workflow/services";
import { useMarkdown } from "@/composables/markdown";
import { withPrefix } from "@/utils/redirect";

import type { TrsSelection, TrsTool as TrsSearchData } from "./types";

import GButton from "@/components/BaseComponents/GButton.vue";
import GTable from "@/components/Common/GTable.vue";
import HelpText from "@/components/Help/HelpText.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import TrsServerSelection from "@/components/Workflow/Import/TrsServerSelection.vue";
import TrsTool from "@/components/Workflow/Import/TrsTool.vue";

const emit = defineEmits<{
    (e: "input-valid", valid: boolean): void;
}>();

type TrsSearchRow = {
    id: string;
    name: string;
    description: string;
    data: TrsSearchData;
};

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const fields: TableField[] = [
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

function showRowDetails({ event, toggleDetails }: RowClickEvent<TrsSearchRow>) {
    if ((event.target as Node | undefined)?.nodeName !== "A") {
        toggleDetails();
    }
}

function computeItems(items: TrsSearchData[]) {
    return items.map((item) => {
        return {
            id: item.id,
            name: item.name,
            description: item.description,
            data: item,
        };
    });
}

const router = useRouter();

function onVersionSelected(toolData: TrsSearchData, versionId: string) {
    selectedTool.value = toolData;
    selectedVersion.value = versionId;
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
    <div class="container workflow-import-trs-search">
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

        <div class="trs-search-field">
            <BInputGroup>
                <BFormInput
                    id="trs-search-query"
                    v-model="query"
                    debounce="500"
                    placeholder="search query"
                    data-description="filter text input"
                    @keyup.esc="query = ''" />

                <BInputGroupAppend>
                    <GButton size="small" title="clear search" @click="query = ''">
                        <FontAwesomeIcon :icon="faTimes" />
                    </GButton>
                </BInputGroupAppend>
            </BInputGroup>
            <HelpText uri="galaxy.workflows.import.searchHelp" info-icon />
        </div>

        <div class="vertical-scroll">
            <BAlert v-if="loading" variant="info" show>
                <LoadingSpan :message="`Searching for ${query}, this may take a while - please be patient`" />
            </BAlert>
            <BAlert v-else-if="!query" variant="info" show> Enter search query to begin search. </BAlert>
            <BAlert v-else-if="results.length == 0" variant="info" show>
                No search results found, refine your search.
            </BAlert>
            <GTable
                v-else
                :fields="fields"
                :items="itemsComputed"
                hover
                caption-top
                clickable-rows
                :loading="loading"
                @row-click="showRowDetails">
                <template v-slot:row-details="{ item }">
                    <BCard>
                        <BAlert v-if="importing" variant="info" show>
                            <LoadingSpan message="Importing workflow" />
                        </BAlert>

                        <TrsTool
                            :trs-tool="item.data"
                            @onImport="onVersionSelected(item.data, $event)"
                            @onSelect="onVersionSelected(item.data, $event)" />
                    </BCard>
                </template>

                <template v-slot:cell(description)="row">
                    <span class="trs-description" v-html="renderMarkdown(row.item.data.description)" />
                </template>
            </GTable>
        </div>
    </div>
</template>

<style scoped lang="scss">
.vertical-scroll {
    max-height: 600px;
    overflow-y: auto;

    .trs-description {
        position: relative;
        overflow: hidden;
        display: -webkit-box;
        -webkit-box-orient: vertical;
        -webkit-line-clamp: 3;
        line-clamp: 3;
    }

    .trs-search-field {
        display: flex;
        gap: var(--spacing);
        align-items: center;
        margin-bottom: var(--spacing-4);

        :deep(.popper-element) {
            max-width: 30vw;
        }
    }
}
</style>
