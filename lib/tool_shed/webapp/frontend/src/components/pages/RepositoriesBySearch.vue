<script setup lang="ts">
import { computed, ref, watch } from "vue"
import PageContainer from "@/components/PageContainer.vue"
import RepositoryGrid from "@/components/RepositoriesGrid.vue"
import { type RepositoryGridItem, type OnScroll } from "@/components/RepositoriesGridInterface"
import { ToolShedApi, components } from "@/schema"
import { notifyOnCatch } from "@/util"

const query = ref("")
const page = ref(1)
const fetchedLastPage = ref(false)
const hits = ref([] as Array<RepositorySearchHit>)

type RepositorySearchHit = components["schemas"]["RepositorySearchHit"]

async function doQuery() {
    const queryValue = query.value

    try {
        const { data } = await ToolShedApi().GET("/api/repositories", {
            params: {
                query: { q: queryValue, page: page.value, page_size: 10 },
            },
        })

        if (query.value != queryValue) {
            console.log("query changed.... not using these results...")
            return
        }

        if (data && "hits" in data) {
            if (page.value == 1) {
                hits.value = data.hits
            } else {
                data.hits.forEach((h) => hits.value.push(h))
            }
            if (hits.value.length >= parseInt(data.total_results)) {
                fetchedLastPage.value = true
            }
            page.value = page.value + 1
        } else {
            throw Error("Server response structure error.")
        }
    } catch (e) {
        notifyOnCatch(e)
    }
}

watch(query, (oldQuery, newQuery) => {
    if (newQuery && oldQuery != newQuery && newQuery.length > 1) {
        page.value = 1
        fetchedLastPage.value = false
        hits.value = []
        doQuery()
    }
})

async function onScrollImpl(): Promise<void> {
    if (!fetchedLastPage.value) {
        doQuery()
    }
}

const OnScrollImpl: OnScroll = onScrollImpl

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

const realRows = computed(() => hits?.value.map(adaptHit))

/*
function rowsFunc() {
    const rows: RepositoryGridItem[] = []
    for (let i = 0; i < page.value; i++) {
        realRows.value.forEach((x, innerIndex) => rows.push({ index: innerIndex + i * realRows.value.length, ...x }))
    }
    return rows
}*/

const rows = realRows
</script>
<template>
    <page-container>
        <q-input debounce="20" filled v-model="query" label="Search Repositories" />
        <repository-grid v-if="query && query.length > 1" :rows="rows" title="Search Results" :on-scroll="OnScrollImpl">
        </repository-grid>
    </page-container>
</template>
