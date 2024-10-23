<script setup lang="ts">
import { computed } from "vue"
import { useCategoriesStore } from "@/stores"
import RepositoriesGrid from "@/components/RepositoriesGrid.vue"
import { nodeToRow } from "@/components/RepositoriesGridInterface"
import ErrorBanner from "@/components/ErrorBanner.vue"
import LoadingDiv from "@/components/LoadingDiv.vue"
import { graphql } from "@/gql"
import type { Query, RelayRepositoryConnection } from "@/gql/graphql"
import { useRelayInfiniteScrollQuery } from "@/relayClient"
const categoriesStore = useCategoriesStore()

const props = defineProps({
    categoryId: {
        type: String,
        required: true,
    },
})

void categoriesStore.getAll()

const category = computed(() => {
    const category = categoriesStore.byId(props.categoryId)
    return category
})

const categoryName = computed(() => {
    return category.value ? category.value.name : "Category"
})

const query = graphql(/* GraphQL */ `
    query repositoriesByCategory($categoryId: String, $cursor: String) {
        relayRepositoriesForCategory(encodedId: $categoryId, sort: NAME_ASC, first: 10, after: $cursor) {
            edges {
                cursor
                node {
                    ...RepositoryListItemFragment
                }
            }
            pageInfo {
                endCursor
                hasNextPage
            }
        }
    }
`)

function toResult(queryResult: Query): RelayRepositoryConnection {
    const result = queryResult.relayRepositoriesForCategory
    if (!result) {
        throw Error("problem")
    }
    return result as RelayRepositoryConnection
}

const { records, error, loading, onScroll } = useRelayInfiniteScrollQuery(
    query,
    { categoryId: props.categoryId },
    toResult
)

const rows = computed(() => {
    return records.value.map(nodeToRow)
})
</script>
<template>
    <loading-div v-if="loading" />
    <error-banner error="Failed to load repository" v-else-if="error"> </error-banner>
    <q-page class="q-pa-md" v-if="categoryName">
        <repositories-grid :title="`Repositories for ${categoryName}`" :rows="rows" :on-scroll="onScroll" />
    </q-page>
</template>
