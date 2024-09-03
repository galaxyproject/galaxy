<script setup lang="ts">
import { ref, computed } from "vue"
import { QTableColumn } from "quasar"

import { RepositoryGridItem, OnScroll } from "./RepositoriesGridInterface"

import RepositoryLink from "@/components/RepositoryLink.vue"
import RepositoryExplore from "@/components/RepositoryExplore.vue"

interface RepositoriesGridProps {
    title?: string
    loading?: boolean
    onScroll?: OnScroll | null
    rows: Array<RepositoryGridItem>
    noDataLabel?: string
    debug?: boolean
}

interface ScrollDetails {
    to: number
    from: number
    index: number
    direction: "increase" | "decrease"
}

const compProps = withDefaults(defineProps<RepositoriesGridProps>(), {
    title: "Repositories",
    loading: false,
    debug: false,
    onScroll: null as OnScroll | null,
    noDataLabel: "No repositories found",
})

const pagination = { rowsPerPage: 0 }

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
    field: "name",
}

const columns = computed(() => {
    if (compProps.debug) {
        return [NAME_COLUMN, INDEX_COLUMN]
    } else {
        return [NAME_COLUMN]
    }
})

const tableLoading = ref(false)

async function onVirtualScroll(details: ScrollDetails) {
    const { to, direction } = details
    if (direction == "decrease") {
        return
    }
    const effectiveTo = to + 1
    if (tableLoading.value !== true && effectiveTo >= compProps.rows.length) {
        if (compProps.onScroll) {
            await compProps.onScroll()
            tableLoading.value = false
        }
    }
}

// Adapt the rows with doubleIndex so
const adaptedRows = computed(() =>
    compProps.rows.map((r) => {
        return { doubleIndex: r.index * 2, ...r }
    })
)
</script>
<template>
    <div class="q-pa-md">
        <q-table
            v-if="loading || rows.length > 0"
            style="height: 85vh"
            :title="title"
            :rows="adaptedRows"
            :columns="columns"
            :loading="tableLoading"
            row-key="newIndex"
            virtual-scroll
            :virtual-scroll-item-size="48"
            :virtual-scroll-sticky-size-start="48"
            :pagination="pagination"
            :rows-per-page-options="[0]"
            :no-data-label="noDataLabel"
            @virtual-scroll="onVirtualScroll"
            hide-header
            hide-bottom
        >
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
                    class="q-virtual-scroll--with-prev disable-hover-hack"
                >
                    <q-td colspan="100%">
                        <span class="text-weight-regular q-ml-md text-grey">
                            {{ props.row.description }}
                        </span>
                    </q-td>
                </q-tr>
            </template>
        </q-table>
        <q-banner rounded class="bg-warning text-white" v-else>
            <!-- the no-data-label doesn't seem to be working,
                 probably because we're overriding the whole body
            -->
            <div class="text-h4">{{ noDataLabel }}</div>
        </q-banner>
    </div>
</template>

<style>
.disable-hover-hack > td::before {
    background: rgba(0, 0, 0, 0) !important;
}
</style>
<!-- https://codepen.io/smolinari/pen/bGVxKPE -->
