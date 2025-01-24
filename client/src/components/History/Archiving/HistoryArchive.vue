<script setup lang="ts">
import { BAlert, BListGroup, BListGroupItem, BPagination } from "bootstrap-vue";
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { GalaxyApi } from "@/api";
import { type ArchivedHistorySummary, fetchArchivedHistories } from "@/api/histories.archived";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { useToast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import DelayedInput from "@/components/Common/DelayedInput.vue";
import ArchivedHistoryCard from "@/components/History/Archiving/ArchivedHistoryCard.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const router = useRouter();
const historyStore = useHistoryStore();
const toast = useToast();
const { confirm } = useConfirmDialog();

const archivedHistories = ref<ArchivedHistorySummary[]>([]);
const isLoading = ref(true);
const perPage = ref(10);
const currentPage = ref(1);
const totalRows = ref(0);
const sortBy = ref("update_time");
const sortDesc = ref(true);
const searchText = ref("");

const noResults = computed(() => totalRows.value === 0);
const hasFilters = computed(() => searchText.value !== "");
const noHistoriesMatchingFilter = computed(() => hasFilters.value && noResults.value);
const showPagination = computed(() => totalRows.value > perPage.value && !isLoading.value && !noResults.value);

onMounted(async () => {
    loadArchivedHistories();
});

watch([searchText, currentPage, perPage, sortBy, sortDesc], () => {
    loadArchivedHistories();
});

async function updateSearchQuery(query: string) {
    searchText.value = query;
}

async function loadArchivedHistories() {
    isLoading.value = true;
    try {
        const result = await fetchArchivedHistories({
            query: searchText.value,
            currentPage: currentPage.value,
            pageSize: perPage.value,
            sortBy: sortBy.value,
            sortDesc: sortDesc.value,
        });
        totalRows.value = result.totalMatches;
        archivedHistories.value = result.histories;
    } catch (error) {
        toast.error(
            localize(`Failed to load archived histories with reason: ${errorMessageAsString(error)}`),
            localize("Loading Failed")
        );
    } finally {
        isLoading.value = false;
    }
}

function onViewHistoryInCenterPanel(history: ArchivedHistorySummary) {
    router.push(`/histories/view?id=${history.id}`);
}

function onSetAsCurrentHistory(history: ArchivedHistorySummary) {
    historyStore.setCurrentHistory(history.id);
}

async function onRestoreHistory(history: ArchivedHistorySummary) {
    const confirmTitle = localize(`Unarchive '${history.name}'?`);
    const confirmMessage =
        history.purged && history.export_record_data
            ? localize(
                  "Are you sure you want to restore this (purged) history? Please note that this will not restore the datasets associated with this history. If you want to fully recover it, you can import a copy from the export record instead."
              )
            : localize(
                  "Are you sure you want to restore this history? This will move the history back to your active histories."
              );
    const confirmed = await confirm(confirmMessage, { title: confirmTitle });
    if (!confirmed) {
        return;
    }
    try {
        const force = true;
        await historyStore.unarchiveHistoryById(history.id, force);
        toast.success(localize(`History '${history.name}' has been restored.`), localize("History Restored"));
        return loadArchivedHistories();
    } catch (error) {
        toast.error(
            localize(`Failed to restore history '${history.name}' with reason: ${error}`),
            localize("History Restore Failed")
        );
    }
}

async function onImportCopy(history: ArchivedHistorySummary) {
    const confirmed = await confirm(
        localize(
            `Are you sure you want to import a new copy of this history? This will create a new history with the same datasets contained in the associated export snapshot.`
        ),
        {
            title: localize(`Import Copy of '${history.name}'?`),
        }
    );
    if (!confirmed) {
        return;
    }

    if (!history.export_record_data) {
        toast.error(
            localize(`Failed to import history '${history.name}' because it does not have an export record.`),
            localize("History Import Failed")
        );
        return;
    }

    const { error } = await GalaxyApi().POST("/api/histories/from_store_async", {
        body: {
            model_store_format: history.export_record_data?.model_store_format,
            store_content_uri: history.export_record_data?.target_uri,
        },
    });

    if (error) {
        toast.error(
            localize(`Failed to import history '${history.name}' with reason: ${error}`),
            localize("History Import Failed")
        );
        return;
    }

    toast.success(
        localize(
            `The History '${history.name}' it's being imported. This process may take a while. Check your histories list after a few minutes.`
        ),
        localize("Importing History in background...")
    );
}
</script>
<template>
    <section id="archived-histories" class="d-flex flex-column">
        <div>
            <DelayedInput
                :value="searchText"
                class="m-1 mb-3"
                placeholder="search by name"
                @change="updateSearchQuery" />
            <BAlert v-if="isLoading" variant="info" show>
                <LoadingSpan v-if="isLoading" message="Loading archived histories" />
            </BAlert>
            <BAlert v-else-if="noHistoriesMatchingFilter" variant="info" show>
                There are no archived histories matching your current filter: <b>{{ searchText }}</b>
            </BAlert>
            <BAlert v-else-if="noResults" variant="info" show>
                You do not have any archived histories. You can select the 'Archive History' option from the history
                menu to archive a history.
            </BAlert>
            <BListGroup v-else>
                <BListGroupItem v-for="history in archivedHistories" :key="history.id" :data-pk="history.id">
                    <ArchivedHistoryCard
                        :history="history"
                        @onView="onViewHistoryInCenterPanel"
                        @onSwitch="onSetAsCurrentHistory"
                        @onRestore="onRestoreHistory"
                        @onImportCopy="onImportCopy" />
                </BListGroupItem>
            </BListGroup>
            <BPagination
                v-if="showPagination"
                v-model="currentPage"
                class="mt-3"
                :total-rows="totalRows"
                :per-page="perPage" />
        </div>
    </section>
</template>
