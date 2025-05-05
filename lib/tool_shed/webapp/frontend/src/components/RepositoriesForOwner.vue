<script setup lang="ts">
import PaginatedRepositoriesGrid from "@/components/PaginatedRepositoriesGrid.vue"
import { adaptPaginatedIndexResponse, type Query, type QueryResults } from "@/components/RepositoriesGridInterface"
import { paginatedIndex } from "@/api"
import { notifyOnCatch } from "@/util"

interface RepositoriesByOwnerProps {
    username: string
}

const props = defineProps<RepositoriesByOwnerProps>()

async function onRequest(query: Query): Promise<QueryResults> {
    try {
        const data = await paginatedIndex({
            page: query.page || 1,
            page_size: query.rowsPerPage,
            owner: props.username,
            filter: query.filter,
        })
        return adaptPaginatedIndexResponse(data)
    } catch (e) {
        notifyOnCatch(e)
        return { items: [], rowsNumber: 0 }
    }
}
</script>
<template>
    <paginated-repositories-grid :title="`Repositories for ${username}`" :on-request="onRequest" :allow-search="true" />
</template>
