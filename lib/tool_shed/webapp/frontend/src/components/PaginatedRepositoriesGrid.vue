<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { useRoute } from "vue-router"
import { QTableColumn, type QTableProps } from "quasar"

import { type Query, RepositoryGridItem, type OnRequest } from "./RepositoriesGridInterface"

const route = useRoute()

const DEFAULT_ROWS_PER_PAGE = 25

const rowsPerPage = computed(() => {
    console.log(route.query)
    const rowsPerPageQuery = route.query.rows_per_page
    if (typeof rowsPerPageQuery == "string") {
        return Number.parseInt(rowsPerPageQuery)
    }
    return DEFAULT_ROWS_PER_PAGE
})

import RepositoryLink from "@/components/RepositoryLink.vue"
import RepositoryExplore from "@/components/RepositoryExplore.vue"

interface RepositoriesGridProps {
    title?: string
    loading?: boolean
    onRequest?: OnRequest
    noDataLabel?: string
    debug?: boolean
    allowSearch?: boolean
}

const compProps = withDefaults(defineProps<RepositoriesGridProps>(), {
    title: "Repositories",
    loading: false,
    debug: false,
    onRequest: undefined as OnRequest | undefined,
    noDataLabel: "No repositories found",
    allowSearch: false,
    rowsNumber: undefined,
})

const pagination = ref({
    page: 1,
    rowsNumber: undefined as number | undefined,
    rowsPerPage: rowsPerPage,
})

const INDEX_COLUMN: QTableColumn = {
    name: "index",
    label: "Index",
    align: "left",
    field: "index",
}

const NAME_COLUMN: QTableColumn = {
    name: "name",
    label: "Name",
    align: "left",
    field: "effectiveName",
}

const columns = computed(() => {
    if (compProps.debug) {
        return [NAME_COLUMN, INDEX_COLUMN]
    } else {
        return [NAME_COLUMN]
    }
})

const tableLoading = ref(false)

const search = ref("")

const rows = ref<RepositoryGridItem[]>([])

// Adapt the rows with doubleIndex so
const adaptedRows = computed(() =>
    rows.value.map((r: RepositoryGridItem) => {
        // create this effective name so we are filtering on this when searching...
        const effectiveName = r.owner + " " + r.name
        return { doubleIndex: r.index * 2, effectiveName: effectiveName, ...r }
    })
)

const onRequest: QTableProps["onRequest"] = async ({ pagination: queryPagination }) => {
    tableLoading.value = true
    const query: Query = {
        page: queryPagination.page,
        rowsPerPage: queryPagination.rowsPerPage,
    }
    if (compProps.allowSearch && search.value) {
        query.filter = search.value
    }
    if (compProps.onRequest) {
        const results = await compProps.onRequest(query)
        rows.value.splice(0, rows.value.length, ...results.items)
        pagination.value.rowsNumber = results.rowsNumber
        pagination.value.page = queryPagination.page
        tableLoading.value = false
    }
}

const table = ref()

function makeRequest() {
    if (table.value) {
        table.value.requestServerInteraction()
    }
}

defineExpose({ makeRequest })

onMounted(() => {
    makeRequest()
})
</script>
<template>
    <div class="q-pa-md">
        <!-- eslint-disable vue/no-v-model-argument -->
        <q-table
            ref="table"
            v-model:pagination="pagination"
            :rows="adaptedRows"
            :columns="columns"
            :loading="tableLoading"
            :filter="search"
            row-key="newIndex"
            :rows-per-page-options="[rowsPerPage]"
            :no-data-label="noDataLabel"
            hide-header
            @request="onRequest"
        >
            <template #top>
                <div class="row col-12">
                    <div class="q-table__control col-8">
                        <div class="q-table__title">{{ title }}</div>
                    </div>
                    <div class="col-4 justify-end q-pa-md" v-if="allowSearch">
                        <q-input v-model="search" autogrow label="Filter"></q-input>
                    </div>
                </div>
            </template>
            <template #body="props">
                <q-tr :props="props" :key="`m_${props.row.index}`">
                    <q-td v-for="col in props.cols" :key="col.name" :props="props">
                        <span class="text-weight-bold">
                            <repository-link :id="props.row.id" :name="props.row.name" :owner="props.row.owner" />
                        </span>
                        <repository-explore :repository="props.row" :dense="true" />
                    </q-td>
                </q-tr>
                <q-tr
                    style="border-color: rgba(0, 0, 0, 0) !important"
                    :props="props"
                    :key="`e_${props.row.index}`"
                    class="disable-hover-hack"
                >
                    <q-td colspan="100%">
                        <span class="text-weight-regular q-ml-md text-grey">
                            {{ props.row.description }}
                        </span>
                    </q-td>
                </q-tr>
            </template>
        </q-table>
    </div>
</template>

<style>
.disable-hover-hack > td::before {
    background: rgba(0, 0, 0, 0) !important;
}
</style>
<!-- https://codepen.io/smolinari/pen/bGVxKPE -->
