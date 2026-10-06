<script setup lang="ts">
import { faMagnifyingGlass } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { GFormInput } from "@galaxyproject/galaxy-ui"
import { watchDebounced } from "@vueuse/core"
import { ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import PageContainer from "@/components/PageContainer.vue"
import PageHeader from "@/components/PageHeader.vue"
import PaginatedRepositoriesGrid from "@/components/PaginatedRepositoriesGrid.vue"
import {
    emptyQueryResults,
    type RepositoryGridItem,
    type Query,
    type QueryResults,
} from "@/components/RepositoriesGridInterface"
import { type components } from "@/schema"
import { repositorySearch } from "@/api"
import { notifyOnCatch, queryParamToString } from "@/util"

const route = useRoute()
const router = useRouter()
// searchInput tracks what's typed immediately; searchQuery is debounced off of it
// so a search (and the URL/grid update that follows) only fires once typing settles.
const searchInput = ref(queryParamToString(route.query.q) ?? "")
const searchQuery = ref(searchInput.value)
let currentSearchId = 0

watchDebounced(searchInput, (newValue) => (searchQuery.value = newValue), { debounce: 1000 })

type RepositorySearchHit = components["schemas"]["RepositorySearchHit"]

async function onRequest(query: Query): Promise<QueryResults> {
    const queryValue = searchQuery.value
    if (!queryValue) {
        return emptyQueryResults()
    }
    const thisSearchId = ++currentSearchId
    try {
        const data = await repositorySearch({
            q: queryValue,
            page: query.page,
            page_size: query.rowsPerPage,
        })
        // Discard results if a newer search has been initiated
        if (thisSearchId !== currentSearchId) {
            return emptyQueryResults()
        }
        return {
            items: data.hits.map(adaptHit),
            rowsNumber: Number.parseInt(data.total_results),
        }
    } catch (e) {
        // Only report errors for current search
        if (thisSearchId === currentSearchId) {
            notifyOnCatch(e)
        }
        return emptyQueryResults()
    }
}

function adaptHit(hit: RepositorySearchHit, index: number): RepositoryGridItem {
    const repository = hit.repository
    return {
        index: index,
        id: repository.id,
        name: repository.name,
        owner: repository.repo_owner_username,
        description: repository.description,
        update_time: repository.full_last_updated,
        homepage_url: repository.homepage_url,
        remote_repository_url: repository.remote_repository_url,
    }
}
const grid = ref()

watch(searchQuery, (newValue) => {
    const query: Record<string, string> = {}
    if (newValue) query.q = newValue
    // Reset to page 1 on new search
    router.replace({ query })
    if (grid.value) {
        grid.value.makeRequest()
    }
})

// Handle browser back/forward navigation
watch(
    () => route.query.q,
    (newQ) => {
        const queryValue = queryParamToString(newQ) ?? ""
        if (queryValue !== searchQuery.value) {
            searchInput.value = queryValue
            searchQuery.value = queryValue
        }
    },
)
</script>
<template>
    <page-container>
        <template #header>
            <page-header title="Search repositories">
                <template #meta>
                    <div class="search-box" role="search">
                        <FontAwesomeIcon :icon="faMagnifyingGlass" class="search-box-icon" aria-hidden="true" />
                        <GFormInput
                            :model-value="searchInput"
                            class="search-box-input"
                            placeholder="Name, owner, or description"
                            aria-label="Search Repositories"
                            @update:model-value="searchInput = $event ?? ''"
                        />
                    </div>
                </template>
            </page-header>
        </template>
        <PaginatedRepositoriesGrid
            ref="grid"
            v-if="searchQuery && searchQuery.length > 1"
            title="Search Results"
            :on-request="onRequest"
            :sync-page-to-url="true"
            no-data-label="No repositories match that search"
        >
        </PaginatedRepositoriesGrid>
        <p v-else class="search-hint">Type at least two characters to search the Tool Shed.</p>
    </page-container>
</template>

<style scoped>
.search-box {
    position: relative;
    width: min(40rem, 100%);
}

.search-box-icon {
    position: absolute;
    top: 50%;
    left: 1rem;
    color: var(--shed-muted);
    transform: translateY(-50%);
    pointer-events: none;
}

.search-box :deep(.search-box-input) {
    width: 100%;
    height: 3rem;
    padding-left: 2.75rem;
    font-size: 1.05rem;
    background: #fff;
    border: none;
    border-radius: 0.6rem;
    box-shadow: 0 6px 20px rgba(10, 14, 28, 0.3);
}

.search-box :deep(.search-box-input:focus) {
    outline: none;
    box-shadow:
        0 6px 20px rgba(10, 14, 28, 0.3),
        0 0 0 3px var(--shed-gold);
}

.search-hint {
    margin: 1rem 0;
    text-align: center;
    color: var(--shed-muted);
}
</style>
