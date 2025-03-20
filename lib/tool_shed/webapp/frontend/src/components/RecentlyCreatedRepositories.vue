<script setup lang="ts">
import { computed } from "vue"
import LoadingDiv from "@/components/LoadingDiv.vue"
import ErrorBanner from "@/components/ErrorBanner.vue"
import { graphql } from "@/gql"
import { useQuery } from "@vue/apollo-composable"
import RepositoryCreation from "@/components/RepositoryCreation.vue"

const query = graphql(`
    query recentlyCreatedRepositories {
        relayRepositories(first: 10, sort: CREATE_TIME_DESC) {
            edges {
                node {
                    ...RepositoryCreationItem
                }
            }
        }
    }
`)
const { loading, error, result } = useQuery(query)
const creations = computed(() => result.value?.relayRepositories?.edges.map((v) => v?.node))
</script>

<template>
    <!-- style="max-width: 350px" -->
    <div class="q-pa-md">
        <q-list bordered padding>
            <q-item-label header>Newest Repositories</q-item-label>
            <error-banner :error="error.message" v-if="error" />
            <loading-div message="Loading most recently created repositories" v-else-if="loading" />
            <div v-else>
                <q-separator spaced />
                <span v-for="creation of creations" :key="(creation as any)?.encodedId">
                    <repository-creation :creation="creation" v-if="creation != undefined" />
                </span>
            </div>
        </q-list>
    </div>
</template>
