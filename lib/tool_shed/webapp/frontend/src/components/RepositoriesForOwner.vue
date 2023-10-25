<script setup lang="ts">
import { computed } from "vue"
import RepositoriesGrid from "@/components/RepositoriesGrid.vue"
import { nodeToRow } from "@/components/RepositoriesGridInterface"
import ErrorBanner from "@/components/ErrorBanner.vue"
import LoadingDiv from "@/components/LoadingDiv.vue"
import { graphql } from "@/gql"
import type { Query, RelayRepositoryConnection } from "@/gql/graphql"
import { useRelayInfiniteScrollQuery } from "@/relayClient"

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

function toResult(queryResult: Query): RelayRepositoryConnection {
    const result = queryResult.relayRepositoriesForOwner
    if (!result) {
        throw Error("problem")
    }
    return result as RelayRepositoryConnection
}

const { records, error, loading, onScroll } = useRelayInfiniteScrollQuery(query, { username: props.username }, toResult)

const rows = computed(() => {
    return records.value.map(nodeToRow)
})
</script>
<template>
    <loading-div v-if="loading" />
    <error-banner error="Failed to load repositories" v-else-if="error"> </error-banner>
    <repositories-grid :title="`Repositories for ${username}`" :rows="rows" :on-scroll="onScroll" />
</template>
