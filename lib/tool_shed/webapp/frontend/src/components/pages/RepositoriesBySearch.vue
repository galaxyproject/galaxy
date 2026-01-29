<script setup lang="ts">
import { ref, watch } from "vue"
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
import { notifyOnCatch } from "@/util"

const searchQuery = ref("")

type RepositorySearchHit = components["schemas"]["RepositorySearchHit"]

async function onRequest(query: Query): Promise<QueryResults> {
    const queryValue = searchQuery.value
    if (!queryValue) {
        return emptyQueryResults()
    }
    try {
        const data = await repositorySearch({
            q: queryValue,
            page: query.page,
            page_size: query.rowsPerPage,
        })
        return {
            items: data.hits.map(adaptHit),
            rowsNumber: Number.parseInt(data.total_results),
        }
    } catch (e) {
        notifyOnCatch(e)
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

watch(searchQuery, () => {
    if (grid.value) {
        grid.value.makeRequest()
    }
})
</script>
<template>
    <page-container>
        <q-input debounce="20" filled v-model="searchQuery" label="Search Repositories" />
        <PaginatedRepositoriesGrid
            ref="grid"
            v-if="searchQuery && searchQuery.length > 1"
            title="Search Results"
            :on-request="onRequest"
        >
        </PaginatedRepositoriesGrid>
    </page-container>
</template>
