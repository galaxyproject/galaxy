<script setup lang="ts">
import { faChevronLeft, faChevronRight, faFilter, faSpinner } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { GButton, GFormInput } from "@galaxyproject/galaxy-ui"
import { watchDebounced } from "@vueuse/core"
import { ref, computed, onMounted, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import { type Query, type QueryResults, RepositoryGridItem, type OnRequest } from "./RepositoriesGridInterface"
import RepositoryLink from "@/components/RepositoryLink.vue"
import RepositoryExplore from "@/components/RepositoryExplore.vue"
import UtcDate from "@/components/UtcDate.vue"
import { notifyOnCatch } from "@/util"

const route = useRoute()
const router = useRouter()

const DEFAULT_ROWS_PER_PAGE = 25
const FILTER_DEBOUNCE_MS = 300

// URL query values are user-editable, so anything that isn't a positive whole number falls back
function positiveInteger(value: unknown, fallback: number): number {
    const parsed = typeof value === "string" ? Number.parseInt(value) : NaN
    return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback
}

const rowsPerPage = computed(() => positiveInteger(route.query.rows_per_page, DEFAULT_ROWS_PER_PAGE))

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

const initialPage = computed(() => positiveInteger(route.query.page, 1))

const page = ref(initialPage.value)
const rowsNumber = ref<number | undefined>(undefined)
const tableLoading = ref(false)
const search = ref("")
const rows = ref<RepositoryGridItem[]>([])

const pageCount = computed(() => Math.max(1, Math.ceil((rowsNumber.value ?? 0) / rowsPerPage.value)))
const firstShown = computed(() => (rows.value.length ? (page.value - 1) * rowsPerPage.value + 1 : 0))
const lastShown = computed(() => (page.value - 1) * rowsPerPage.value + rows.value.length)
const countLabel = computed(() => {
    const count = rowsNumber.value ?? 0
    return `${count} ${count === 1 ? "repository" : "repositories"}`
})

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
    let results: QueryResults
    try {
        results = await compProps.onRequest(query)
    } catch (e) {
        if (thisRequest === latestRequest) {
            tableLoading.value = false
            notifyOnCatch(e)
        }
        return
    }
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

// A new filter starts the results over from the first page, once typing pauses
watchDebounced(
    search,
    () => {
        void requestPage(1)
    },
    { debounce: FILTER_DEBOUNCE_MS },
)

// Handle browser back/forward navigation for page
watch(
    () => route.query.page,
    (newPage) => {
        if (!compProps.syncPageToUrl) return
        const pageNum = positiveInteger(newPage, 1)
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
    <!-- The page names what is listed (in its header); the grid labels its list with the same title -->
    <section class="repositories-grid shed-card" :aria-busy="tableLoading" :aria-label="title">
        <div class="grid-top">
            <h2 v-if="rowsNumber !== undefined" class="grid-count">{{ countLabel }}</h2>
            <div v-if="allowSearch" class="grid-filter">
                <FontAwesomeIcon :icon="faFilter" class="grid-filter-icon" aria-hidden="true" />
                <GFormInput
                    v-model="search"
                    class="grid-filter-input"
                    placeholder="Filter these repositories"
                    aria-label="Filter"
                />
            </div>
        </div>

        <ul v-if="rows.length" class="repository-list" :aria-label="title">
            <li v-for="row in rows" :key="`m_${row.index}`" class="repository-entry">
                <div class="repository-entry-main">
                    <span class="repository-entry-name">
                        <repository-link :id="row.id" :name="row.name" :owner="row.owner" />
                    </span>
                    <p v-if="row.description" class="repository-entry-description">{{ row.description }}</p>
                    <p v-if="row.update_time" class="repository-entry-meta">
                        Updated <utc-date :date="row.update_time" mode="elapsed" />
                        <span v-if="debug" class="repository-entry-index">#{{ row.index }}</span>
                    </p>
                </div>
                <repository-explore
                    class="repository-entry-actions"
                    :repository="row"
                    :dense="true"
                    :show-details-link="true"
                />
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
                outline
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
                outline
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
    overflow: hidden;
}

.grid-top {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem 1rem;
    padding: 0.85rem 1.25rem;
    background: color-mix(in srgb, var(--shed-page-bg) 55%, white);
    border-bottom: 1px solid var(--shed-border);
}

.grid-count {
    margin: 0;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--shed-muted);
}

.grid-filter {
    position: relative;
    flex: 0 1 20rem;
    /* Stays right-aligned before the count heading has rendered */
    margin-left: auto;
}

.grid-filter-icon {
    position: absolute;
    top: 50%;
    left: 0.75rem;
    font-size: 0.8rem;
    color: var(--shed-muted);
    transform: translateY(-50%);
    pointer-events: none;
}

.grid-filter :deep(.grid-filter-input) {
    width: 100%;
    padding-left: 2rem;
    background: #fff;
}

.repository-list {
    margin: 0;
    padding: 0;
    list-style: none;
}

.repository-entry {
    position: relative;
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    padding: 1rem 1.25rem;
    transition: background-color var(--shed-transition);
}

.repository-entry + .repository-entry {
    border-top: 1px solid var(--shed-border-subtle);
}

/* The Hub's gold hover bar */
.repository-entry::before {
    content: "";
    position: absolute;
    inset: 0 auto 0 0;
    width: 3px;
    background: var(--shed-gold);
    transform: scaleY(0);
    transition: transform var(--shed-transition);
}

.repository-entry:hover {
    background: color-mix(in srgb, var(--shed-page-bg) 40%, white);
}

.repository-entry:hover::before {
    transform: scaleY(1);
}

.repository-entry-main {
    flex: 1;
    min-width: 0;
}

.repository-entry-name {
    font-size: 1.05rem;
    overflow-wrap: anywhere;
}

.repository-entry-description {
    margin: 0.25rem 0 0;
    color: var(--shed-text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.repository-entry-meta {
    margin: 0.25rem 0 0;
    font-size: 0.82rem;
    color: var(--shed-muted);
}

.repository-entry-index {
    margin-left: 0.5rem;
}

.repository-entry-actions {
    flex: none;
}

.grid-empty,
.grid-loading {
    margin: 0;
    padding: 2.5rem 1.25rem;
    text-align: center;
    color: var(--shed-muted);
}

.grid-pager {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 0.5rem;
    padding: 0.75rem 1.25rem;
    color: var(--shed-text);
    border-top: 1px solid var(--shed-border);
}

.grid-range {
    margin-right: auto;
    color: var(--shed-muted);
}

@media (max-width: 599px) {
    .repository-entry-description {
        white-space: normal;
    }
}
</style>
