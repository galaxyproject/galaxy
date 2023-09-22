<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import localize from "@/utils/localization";
import UtcDate from "@/components/UtcDate.vue";
import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
import * as ArchiveServices from "@/stores/services/historyArchive.services";
import {
    reimportHistoryFromExportRecordAsync,
    type ArchivedHistorySummary,
} from "@/stores/services/historyArchive.services";
import { BAlert, BButton, BButtonGroup, BBadge, BPagination, BListGroup, BListGroupItem } from "bootstrap-vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faUndo, faCopy, faEye } from "@fortawesome/free-solid-svg-icons";
import { useRouter } from "vue-router/composables";
import { useHistoryStore } from "@/stores/historyStore";
import { useToast } from "@/composables/toast";
import { useConfirmDialog } from "@/composables/confirmDialog";

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

library.add(faUndo, faCopy, faEye);

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
    const result = await ArchiveServices.fetchArchivedHistories({
        query: searchText.value,
        currentPage: currentPage.value,
        pageSize: perPage.value,
        sortBy: sortBy.value,
        sortDesc: sortDesc.value,
    });
    totalRows.value = result.totalMatches;
    archivedHistories.value = result.histories;
    isLoading.value = false;
}

function canImportCopy(history: ArchivedHistorySummary) {
    return history.export_record_data?.target_uri !== undefined;
}

function onViewHistoryInCenterPanel(history: ArchivedHistorySummary) {
    router.push(`/histories/view?id=${history.id}`);
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

    try {
        await reimportHistoryFromExportRecordAsync(history);
        toast.success(
            localize(
                `The History '${history.name}' it's being imported. This process may take a while. Check your histories list after a few minutes.`
            ),
            localize("Importing History in background...")
        );
    } catch (error) {
        toast.error(
            localize(`Failed to import history '${history.name}' with reason: ${error}`),
            localize("History Import Failed")
        );
    }
}
</script>
<template>
    <section id="archived-histories" class="d-flex flex-column">
        <h1>Archived Histories</h1>
        <div>
            <delayed-input
                :query="searchText"
                class="m-1 mb-3"
                placeholder="Search by name"
                @change="updateSearchQuery" />
            <b-alert v-if="isLoading" variant="info" show>
                <loading-span v-if="isLoading" message="Loading archived histories" />
            </b-alert>
            <b-alert v-else-if="noHistoriesMatchingFilter" variant="info" show>
                There are no archived histories matching your current filter: <b>{{ searchText }}</b>
            </b-alert>
            <b-alert v-else-if="noResults" variant="info" show>
                You do not have any archived histories. You can select the 'Archive History' option from the history
                menu to archive a history.
            </b-alert>
            <b-list-group v-else>
                <b-list-group-item v-for="history in archivedHistories" :key="history.id" :data-pk="history.id">
                    <div class="d-flex justify-content-between align-items-center">
                        <Heading h3 inline bold size="sm">
                            {{ history.name }}
                        </Heading>

                        <div class="d-flex align-items-center flex-gapx-1 badges">
                            <b-badge
                                v-if="history.published"
                                v-b-tooltip
                                pill
                                :title="localize('This history is public.')">
                                {{ localize("Published") }}
                            </b-badge>
                            <b-badge
                                v-if="!history.purged"
                                v-b-tooltip
                                pill
                                :title="localize('Amount of items in history')">
                                {{ history.count }} {{ localize("items") }}
                            </b-badge>
                            <b-badge
                                v-if="history.export_record_data"
                                v-b-tooltip
                                pill
                                :title="
                                    localize(
                                        'This history has an associated export record containing a snapshot of the history that can be used to import a copy of the history.'
                                    )
                                ">
                                {{ localize("Snapshot available") }}
                            </b-badge>
                            <b-badge v-b-tooltip pill :title="localize('Last edited/archived')">
                                <UtcDate :date="history.update_time" mode="elapsed" />
                            </b-badge>
                        </div>
                    </div>

                    <div class="d-flex justify-content-start align-items-center mt-1">
                        <b-button-group class="actions">
                            <b-button
                                v-b-tooltip
                                :title="localize('View this history')"
                                variant="link"
                                class="p-0 px-1"
                                @click.stop="() => onViewHistoryInCenterPanel(history)">
                                <FontAwesomeIcon icon="fa-eye" size="lg" />
                                View
                            </b-button>
                            <b-button
                                v-b-tooltip
                                :title="localize('Unarchive this history and move it back to your active histories')"
                                variant="link"
                                class="p-0 px-1"
                                @click.stop="() => onRestoreHistory(history)">
                                <FontAwesomeIcon icon="fa-undo" size="lg" />
                                Unarchive
                            </b-button>

                            <b-button
                                v-if="canImportCopy(history)"
                                v-b-tooltip
                                :title="localize('Import a new copy of this history from the associated export record')"
                                variant="link"
                                class="p-0 px-1"
                                @click.stop="() => onImportCopy(history)">
                                <FontAwesomeIcon icon="fa-copy" size="lg" />
                                Import Copy
                            </b-button>
                        </b-button-group>
                    </div>

                    <p v-if="history.annotation" class="my-1">{{ history.annotation }}</p>

                    <StatelessTags class="my-1" :value="history.tags" :disabled="true" :max-visible-tags="10" />
                </b-list-group-item>
            </b-list-group>
            <b-pagination
                v-if="showPagination"
                v-model="currentPage"
                class="mt-3"
                :total-rows="totalRows"
                :per-page="perPage" />
        </div>
    </section>
</template>

<style scoped>
.badges {
    font-size: 1rem;
}
</style>
