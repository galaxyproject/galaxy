<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { BAlert, BTable, BButton, BInputGroup, BInputGroupAppend, BFormInput } from "bootstrap-vue";
import DebouncedInput from "@/components/DebouncedInput";
import LoadingSpan from "@/components/LoadingSpan.vue";
import UtcDate from "@/components/UtcDate.vue";
import type { HistorySummary } from "@/stores/historyStore";

export interface ArchivedHistorySummary extends HistorySummary {
    archived_time: string;
    import_source?: string;
}

const archivedHistories = ref<ArchivedHistorySummary[]>([]);
const isLoading = ref(true);

const perPage = ref(50);
const currentPage = ref(1);
const sortBy = ref("archived_time");
const sortDesc = ref(false);
const filterText = ref("");
const fields = [
    { key: "name", sortable: true },
    { key: "annotation", sortable: false },
    { label: "Archived", key: "archived_time", sortable: true },
    { label: "Contents Available", key: "purged", sortable: true },
    { key: "actions", sortable: false },
];

const isArchiveEmpty = computed(() => archivedHistories.value.length === 0);

const localFilter = computed({
    get() {
        return filterText.value;
    },
    set(newVal) {
        if (newVal !== filterText.value) {
            updateFilter(newVal);
        }
    },
});

function updateFilter(newVal: string, append = false) {
    let oldValue = filterText.value;
    if (append) {
        oldValue += newVal;
    } else {
        oldValue = newVal;
    }
    filterText.value = oldValue.trim();
}

onMounted(() => {
    loadArchivedHistories();
});

async function loadArchivedHistories() {
    isLoading.value = true;
    archivedHistories.value = await getArchivedHistories();
    isLoading.value = false;
}

// TODO: Replace this with the appropriate historyStore method.
async function getArchivedHistories(): Promise<ArchivedHistorySummary[]> {
    // Returns a fake list of ArchivedHistorySummary for now.
    return [
        {
            id: "b2486a20bc56b90f",
            name: "History 1",
            annotation: "This is a test history",
            count: 10,
            tags: [],
            deleted: false,
            purged: false,
            published: false,
            model_class: "History",
            url: "/api/histories/1",
            archived_time: "2021-05-06T15:00:00.000Z",
        },
        {
            id: "0c1da521da72c0b0",
            name: "Deleted History",
            annotation: "This is a test history",
            count: 10,
            tags: [],
            deleted: false,
            purged: true,
            published: false,
            model_class: "History",
            url: "/api/histories/2",
            import_source: "gxfiles://test-posix-source/b2486a20bc56b90f_Tester.rocrate.zip",
            archived_time: "2022-02-09T15:00:00.000Z",
        },
    ];
}
</script>
<template>
    <section id="archived-histories" class="d-flex flex-column">
        <h1>Archived Histories</h1>

        <b-alert v-if="isLoading" variant="info" show>
            <loading-span message="Loading archived histories..." />
        </b-alert>
        <b-alert v-else-if="isArchiveEmpty" variant="info" show> You do not have any archived histories. </b-alert>
        <div v-else>
            <b-input-group class="mb-2">
                <debounced-input v-slot="{ value, input }" v-model="localFilter">
                    <b-form-input
                        id="archived-histories-filter"
                        size="sm"
                        :class="filterText && 'font-weight-bold'"
                        :value="value"
                        placeholder="Filter by name or annotation"
                        title="clear search (esc)"
                        data-description="filter text input"
                        @input="input"
                        @keyup.esc="updateFilter('')" />
                </debounced-input>
                <b-input-group-append>
                    <b-button
                        size="sm"
                        aria-label="Clear filters"
                        data-description="clear filters"
                        @click="updateFilter('')">
                        <icon icon="times" />
                    </b-button>
                </b-input-group-append>
            </b-input-group>
            <b-table
                id="archived-histories-table"
                no-sort-reset
                no-local-sorting
                striped
                :fields="fields"
                :items="archivedHistories"
                :per-page="perPage"
                :current-page="currentPage"
                :sort-by.sync="sortBy"
                :sort-desc.sync="sortDesc">
                <template v-slot:cell(name)="row">
                    <router-link :to="`/histories/view?id=${row.item.id}`">{{ row.item.name }}</router-link>
                </template>
                <template v-slot:cell(archived_time)="data">
                    <UtcDate :date="data.value" mode="elapsed" />
                </template>
                <template v-slot:cell(purged)="data">
                    <span v-if="data.value">No</span>
                    <span v-else>Yes</span>
                </template>
                <template v-slot:cell(actions)="row">
                    <b-button v-if="!row.item.purged" variant="primary" size="sm"> Restore </b-button>
                    <b-button v-if="row.item.import_source" variant="primary" size="sm"> Import Copy </b-button>
                </template>
            </b-table>
        </div>
    </section>
</template>
