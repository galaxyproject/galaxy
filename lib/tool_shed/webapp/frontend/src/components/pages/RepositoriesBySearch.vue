<script setup lang="ts">
import { GFormInput, GFormLabel } from "@galaxyproject/galaxy-ui"
import { watchDebounced } from "@vueuse/core"
import { ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import PageContainer from "@/components/PageContainer.vue"
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
        <GFormLabel title="Search Repositories">
            <GFormInput :model-value="searchInput" @update:model-value="searchInput = $event ?? ''" />
        </GFormLabel>
        <PaginatedRepositoriesGrid
            ref="grid"
            v-if="searchQuery && searchQuery.length > 1"
            title="Search Results"
            :on-request="onRequest"
            :sync-page-to-url="true"
        >
        </PaginatedRepositoriesGrid>
    </page-container>
</template>
