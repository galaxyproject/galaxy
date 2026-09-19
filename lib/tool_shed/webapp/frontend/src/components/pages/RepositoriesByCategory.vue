<script setup lang="ts">
import { computed } from "vue"
import PaginatedRepositoriesGrid from "@/components/PaginatedRepositoriesGrid.vue"
import { useCategoriesStore } from "@/stores"
import { adaptPaginatedIndexResponse, type Query, type QueryResults } from "@/components/RepositoriesGridInterface"
import { paginatedIndex } from "@/api"
import { notifyOnCatch } from "@/util"

interface Props {
    categoryId: string
}

const categoriesStore = useCategoriesStore()
categoriesStore.getAll()
const category = computed(() => {
    const category = categoriesStore.byId(props.categoryId)
    return category
})

const categoryName = computed(() => {
    return category.value ? category.value.name : "Category"
})

const props = defineProps<Props>()

async function onRequest(query: Query): Promise<QueryResults> {
    try {
        const data = await paginatedIndex({
            page: query.page || 1,
            page_size: query.rowsPerPage,
            category_id: props.categoryId,
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
    <q-page class="q-pa-md" v-if="categoryName">
        <paginated-repositories-grid :title="categoryName" :on-request="onRequest" :allow-search="true" />
    </q-page>
</template>
