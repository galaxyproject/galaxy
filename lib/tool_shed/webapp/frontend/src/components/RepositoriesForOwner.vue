<script setup lang="ts">
import { computed } from "vue"
import RepositoriesGrid from "@/components/RepositoriesGrid.vue"
import { nodeToRow } from "@/components/RepositoriesGridInterface"
import ErrorBanner from "@/components/ErrorBanner.vue"
import LoadingDiv from "@/components/LoadingDiv.vue"
import { graphql } from "@/gql"
import { useQuery } from "@vue/apollo-composable"

interface RepositoriesByOwnerProps {
    username: string
}

const props = defineProps<RepositoriesByOwnerProps>()

const query = graphql(/* GraphQL */ `
    query repositoriesByOwner($username: String, $cursor: String) {
        relayRepositoriesForOwner(username: $username, sort: UPDATE_TIME_DESC, first: 10, after: $cursor) {
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
    const cursor = result.value?.relayRepositoriesForOwner?.pageInfo.endCursor || null
    fetchMore({
        variables: {
            username: props.username,
            cursor: cursor,
        },
        // eslint-disable-next-line @typescript-eslint/ban-ts-comment
        // @ts-ignore
        updateQuery: (previousResult, { fetchMoreResult }) => {
            const newRepos = fetchMoreResult?.relayRepositoriesForOwner?.edges || []
            const edges = [...(previousResult?.relayRepositoriesForOwner?.edges || []), ...newRepos]
            const pageInfo = { ...fetchMoreResult?.relayRepositoriesForOwner?.pageInfo }
            return {
                relayRepositoriesForOwner: {
                    __typename: fetchMoreResult?.relayRepositoriesForOwner?.__typename,
                    // Merging the tag list
                    edges: edges,
                    pageInfo: pageInfo,
                },
            }
        },
    })
}
const { result, loading, error, fetchMore } = useQuery(query, { username: props.username })
const rows = computed(() => {
    const nodes = result.value?.relayRepositoriesForOwner?.edges.map((v) => v?.node)
    return nodes?.map(nodeToRow) || []
})
</script>
<template>
    <loading-div v-if="loading" />
    <error-banner error="Failed to load repositories" v-else-if="error"> </error-banner>
    <repositories-grid :title="`Repositories for ${username}`" :rows="rows" :on-scroll="onScroll" />
</template>
