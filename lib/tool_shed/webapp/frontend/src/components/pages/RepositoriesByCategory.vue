<script setup lang="ts">
import { computed } from "vue"
import { useCategoriesStore } from "@/stores"
import RepositoriesGrid from "@/components/RepositoriesGrid.vue"
import { nodeToRow } from "@/components/RepositoriesGridInterface"
import ErrorBanner from "@/components/ErrorBanner.vue"
import LoadingDiv from "@/components/LoadingDiv.vue"
import { graphql } from "@/gql"
import { useQuery } from "@vue/apollo-composable"

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
        relayRepositoriesForCategory(encodedId: $categoryId, sort: UPDATE_TIME_DESC, first: 10, after: $cursor) {
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

async function onScroll(): Promise<void> {
    const cursor = result.value?.relayRepositoriesForCategory?.pageInfo.endCursor || null
    fetchMore({
        variables: {
            categoryId: props.categoryId,
            cursor: cursor,
        },
        // eslint-disable-next-line @typescript-eslint/ban-ts-comment
        // @ts-ignore
        updateQuery: (previousResult, { fetchMoreResult }) => {
            const newRepos = fetchMoreResult?.relayRepositoriesForCategory?.edges || []
            const edges = [...(previousResult?.relayRepositoriesForCategory?.edges || []), ...newRepos]
            const pageInfo = { ...fetchMoreResult?.relayRepositoriesForCategory?.pageInfo }
            return {
                relayRepositoriesForCategory: {
                    __typename: fetchMoreResult?.relayRepositoriesForCategory?.__typename,
                    // Merging the tag list
                    edges: edges,
                    pageInfo: pageInfo,
                },
            }
        },
    })
}

const { result, loading, error, fetchMore } = useQuery(query, { categoryId: props.categoryId })
const rows = computed(() => {
    const nodes = result.value?.relayRepositoriesForCategory?.edges.map((v) => v?.node)
    return nodes?.map(nodeToRow) || []
})
</script>
<template>
    <loading-div v-if="loading" />
    <error-banner error="Failed to load repository" v-else-if="error"> </error-banner>
    <q-page class="q-pa-md" v-if="categoryName">
        <repositories-grid :title="`Repositories for ${categoryName}`" :rows="rows" :on-scroll="onScroll" />
    </q-page>
</template>
