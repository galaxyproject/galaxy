<script setup lang="ts">
import { faChevronLeft, faChevronRight, faSpinner } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { GButton, GFormInput, GFormLabel } from "@galaxyproject/galaxy-ui"
import { ref, computed, onMounted, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import { type Query, RepositoryGridItem, type OnRequest } from "./RepositoriesGridInterface"
import RepositoryLink from "@/components/RepositoryLink.vue"
import RepositoryExplore from "@/components/RepositoryExplore.vue"

const route = useRoute()
const router = useRouter()

const DEFAULT_ROWS_PER_PAGE = 25

const rowsPerPage = computed(() => {
    const rowsPerPageQuery = route.query.rows_per_page
    if (typeof rowsPerPageQuery == "string") {
        return Number.parseInt(rowsPerPageQuery)
    }
    return DEFAULT_ROWS_PER_PAGE
})

interface RepositoriesGridProps {
    title?: string
    loading?: boolean
    onRequest?: OnRequest
    noDataLabel?: string
    debug?: boolean
    allowSearch?: boolean
    syncPageToUrl?: boolean
}

const compProps = withDefaults(defineProps<RepositoriesGridProps>(), {
    title: "Repositories",
    loading: false,
    debug: false,
    onRequest: undefined as OnRequest | undefined,
    noDataLabel: "No repositories found",
    allowSearch: false,
    syncPageToUrl: false,
})

const initialPage = computed(() => {
    const pageQuery = route.query.page
    if (typeof pageQuery == "string") {
        return Number.parseInt(pageQuery)
    }
    return 1
})

const page = ref(initialPage.value)
const rowsNumber = ref<number | undefined>(undefined)
const tableLoading = ref(false)
const search = ref("")
const rows = ref<RepositoryGridItem[]>([])

const pageCount = computed(() => Math.max(1, Math.ceil((rowsNumber.value ?? 0) / rowsPerPage.value)))
const firstShown = computed(() => (rows.value.length ? (page.value - 1) * rowsPerPage.value + 1 : 0))
const lastShown = computed(() => (page.value - 1) * rowsPerPage.value + rows.value.length)

// Responses can land out of order when the filter changes quickly; only the latest one counts
let latestRequest = 0

async function requestPage(pageNumber: number) {
    if (!compProps.onRequest) {
        return
    }
    const thisRequest = ++latestRequest
    tableLoading.value = true
    const query: Query = { page: pageNumber, rowsPerPage: rowsPerPage.value }
    if (compProps.allowSearch && search.value) {
        query.filter = search.value
    }
    const results = await compProps.onRequest(query)
    if (thisRequest !== latestRequest) {
        return
    }
    rows.value.splice(0, rows.value.length, ...results.items)
    rowsNumber.value = results.rowsNumber
    page.value = pageNumber
    tableLoading.value = false

    if (compProps.syncPageToUrl) {
        const newQuery = { ...route.query }
        if (pageNumber > 1) {
            newQuery.page = String(pageNumber)
        } else {
            delete newQuery.page
        }
        router.replace({ query: newQuery })
    }
}

function makeRequest() {
    void requestPage(page.value)
}

defineExpose({ makeRequest })

// A new filter starts the results over from the first page
watch(search, () => {
    void requestPage(1)
})

// Handle browser back/forward navigation for page
watch(
    () => route.query.page,
    (newPage) => {
        if (!compProps.syncPageToUrl) return
        const pageNum = typeof newPage === "string" ? Number.parseInt(newPage) : 1
        if (pageNum !== page.value) {
            void requestPage(pageNum)
        }
    },
)

watch(rowsPerPage, () => {
    void requestPage(1)
})

onMounted(() => {
    makeRequest()
})
</script>
<template>
    <section class="repositories-grid" :aria-busy="tableLoading">
        <div class="grid-top">
            <h1 class="grid-title">{{ title }}</h1>
            <div v-if="allowSearch" class="grid-filter">
                <GFormLabel title="Filter">
                    <GFormInput :model-value="search" @update:model-value="search = $event ?? ''" />
                </GFormLabel>
            </div>
        </div>

        <ul v-if="rows.length" class="repository-list" :aria-label="title">
            <li v-for="row in rows" :key="`m_${row.index}`" class="repository-entry">
                <div class="repository-entry-header">
                    <span class="repository-entry-name">
                        <repository-link :id="row.id" :name="row.name" :owner="row.owner" />
                    </span>
                    <repository-explore :repository="row" :dense="true" :show-details-link="true" />
                    <span v-if="debug" class="repository-entry-index">#{{ row.index }}</span>
                </div>
                <p v-if="row.description" class="repository-entry-description">{{ row.description }}</p>
            </li>
        </ul>
        <p v-else-if="!tableLoading" class="grid-empty">{{ noDataLabel }}</p>

        <div v-if="tableLoading" class="grid-loading" role="status">
            <FontAwesomeIcon :icon="faSpinner" spin aria-hidden="true" />
            Loading repositories
        </div>

        <nav v-if="pageCount > 1" class="grid-pager" :aria-label="`${title} pages`">
            <span class="grid-range">{{ firstShown }}-{{ lastShown }} of {{ rowsNumber }}</span>
            <GButton
                icon-only
                transparent
                title="Previous page"
                aria-label="Previous page"
                :disabled="page <= 1 || tableLoading"
                @click="requestPage(page - 1)"
            >
                <FontAwesomeIcon :icon="faChevronLeft" />
            </GButton>
            <span class="grid-page">Page {{ page }} of {{ pageCount }}</span>
            <GButton
                icon-only
                transparent
                title="Next page"
                aria-label="Next page"
                :disabled="page >= pageCount || tableLoading"
                @click="requestPage(page + 1)"
            >
                <FontAwesomeIcon :icon="faChevronRight" />
            </GButton>
        </nav>
    </section>
</template>

<style scoped>
.repositories-grid {
    padding: var(--spacing-4);
}

.grid-top {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    justify-content: space-between;
    gap: var(--spacing-4);
    margin-bottom: var(--spacing-2);
}

.grid-title {
    margin: 0;
    font-size: 1.25rem;
    font-weight: normal;
}

.grid-filter {
    min-width: 15rem;
}

.repository-list {
    margin: 0;
    padding: 0;
    list-style: none;
    border-top: 1px solid var(--color-grey-200);
}

.repository-entry {
    padding: var(--spacing-2) var(--spacing-4);
    border-bottom: 1px solid var(--color-grey-200);
}

.repository-entry-header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--spacing-2);
}

.repository-entry-name {
    font-weight: bold;
}

.repository-entry-index {
    color: var(--color-grey-500);
    font-size: var(--font-size-small);
}

.repository-entry-description {
    margin: var(--spacing-1) 0 0 var(--spacing-4);
    color: var(--color-grey-600);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.grid-empty,
.grid-loading {
    padding: var(--spacing-4);
    color: var(--color-grey-600);
}

.grid-pager {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: var(--spacing-2);
    padding-top: var(--spacing-3);
    color: var(--color-grey-700);
}

.grid-range {
    margin-right: var(--spacing-4);
}
</style>
