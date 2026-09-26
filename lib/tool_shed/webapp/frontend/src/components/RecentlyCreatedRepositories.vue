<script setup lang="ts">
import { ref, onMounted } from "vue"
import type { Repository } from "@/api"
import { errorMessageAsString } from "@/util"
import { recentlyCreatedRepositories } from "@/api"
import LoadingDiv from "@/components/LoadingDiv.vue"
import ErrorBanner from "@/components/ErrorBanner.vue"
import RepositoryCreation from "@/components/RepositoryCreation.vue"

const error = ref<string>()
const loading = ref(true)
const repositories = ref<Repository[]>()

onMounted(async () => {
    try {
        const repos = await recentlyCreatedRepositories()
        repositories.value = repos["hits"]
    } catch (e) {
        error.value = errorMessageAsString(e)
    } finally {
        loading.value = false
    }
})
</script>

<template>
    <!-- style="max-width: 350px" -->
    <div class="q-pa-md">
        <q-list bordered padding>
            <q-item-label header>Newest Repositories</q-item-label>
            <error-banner :error="error" v-if="error" />
            <loading-div message="Loading most recently created repositories" v-else-if="loading" />
            <div v-else>
                <q-separator spaced />
                <span v-for="repository of repositories" :key="repository.id">
                    <repository-creation :repository="repository" />
                </span>
            </div>
        </q-list>
    </div>
</template>
