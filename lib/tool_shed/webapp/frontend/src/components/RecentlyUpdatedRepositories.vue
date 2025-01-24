<script setup lang="ts">
import { computed } from "vue"
import LoadingDiv from "@/components/LoadingDiv.vue"
import ErrorBanner from "@/components/ErrorBanner.vue"
import { graphql } from "@/gql"
import { useQuery } from "@vue/apollo-composable"
import RepositoryUpdate from "./RepositoryUpdate.vue"

const query = graphql(`
    query recentRepositoryUpdates {
        relayRepositories(first: 10, sort: UPDATE_TIME_DESC) {
            edges {
                node {
                    ...RepositoryUpdateItem
                }
            }
        }
    }
`)
const { loading, error, result } = useQuery(query)
const updates = computed(() => result.value?.relayRepositories?.edges.map((v) => v?.node))
</script>

<template>
    <!-- style="max-width: 350px" -->
    <div class="q-pa-md">
        <q-list bordered padding>
            <q-item-label header>Latest Updates</q-item-label>
            <error-banner :error="error.message" v-if="error" />
            <loading-div message="Loading latest updates" v-else-if="loading" />
            <div v-else-if="updates">
                <q-separator spaced />
                <span v-for="update of updates" :key="(update as any).encodedId">
                    <repository-update :update="update" v-if="update != undefined" />
                </span>
            </div>
        </q-list>
    </div>
</template>
